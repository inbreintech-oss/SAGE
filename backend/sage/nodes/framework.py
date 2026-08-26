"""NodeV framework — LLM codegen loop, validators, and validated.md lesson learning."""

import ast
import asyncio
import importlib.util
import json
import os
import re
import sys
import time
import traceback
from abc import abstractmethod, ABC
from datetime import datetime
from pathlib import Path
from typing import Type, TypeVar, Callable, Optional, List, Any, Protocol, Dict, Tuple
import inspect

import yaml
from pydantic import (BaseModel, Field,
                      ValidationError)
from google.genai.errors import ServerError

import cfg
from sage import data
from sage import prompt as pp
from sage.nodes.lesson_learn import (
    LessonAccumulator,
    consolidate_events,
    compress_error_for_lesson,
    error_signature,
    format_retry_feedback,
    format_validator_retry_user_block,
    format_validator_system_priority_block,
    format_record_only_feedback,
    format_structured_lesson,
    infer_lesson_category,
    llm_reconcile_validated_md,
)
from sage.nodes.validated_md import (
    MAX_PROMPT_CHARS,
    MAX_PROMPT_LINES,
    is_lesson_saveable,
    normalize_lesson,
    prepare_for_prompt,
    reconcile_validated_file,
)
from sage.db import saged
from sage.errs import (
    ServiceUnavailableError,
    MaxRetriesExceededError,
    CodegenContractError,
    QuotaExceededError,
    LLMTimeoutError,
    ContextAttachTooLargeError,
    is_quota_error,
)

from sage.llm import LLMInterface, LLMFactory, Message, GeminiLLM, CursorLLM
from sage.llm.prompt_telemetry import log_prompt_before_llm
from sage.logg import debug, error, warning

from sage.models.node import ToDoList, TaskInput, DataQuery, UserQuery, SourceErr, SourceFixed, \
    TaskUpdateInput, SourceMetadata, DataAnalysisInput, DataAnalysisOutput, DataExecutionInput
from sage.models.tool import ToolPack, ToolErr

T_out = TypeVar("T_out", bound=BaseModel)

class NodeProtocol(Protocol[T_out]):
    async def run(self, **kwargs) -> T_out: ...

def node(*,
         input: Type[BaseModel],
         output: Type[BaseModel],
         llm_types: Optional[List[str]] = None) -> Callable[[Type[Any]], Type[NodeProtocol[T_out]]]:
    """NodeV 서브클래스에 입·출력 Pydantic 모델과 LLM 타입 목록을 부착.

    NodeFactory 가 main.py 로드 시 __node_input_model__ 존재 여부로 노드 클래스를 식별합니다.
    """

    def decorator(cls: Type[Any]) -> Type[NodeProtocol[T_out]]:
        # 런타임 속성 부여
        setattr(cls, '__node_input_model__', input)
        setattr(cls, '__node_output_model__', output)

        if llm_types is None:
            # LLMFactory는 프로젝트 상황에 맞춰 임포트 필요
            setattr(cls, '__llm_types__', [LLMFactory.DEFAULT_LLM_TYPE])
        else:
            setattr(cls, '__llm_types__', llm_types)

        # 중요: 원본 클래스(cls)를 그대로 반환하여 타입 힌트 유지
        return cls  # type: ignore

    return decorator

def output_from_raw_response(input_text: str):
    """
    도구 명세와 모든 Python 함수 정의를 추출하여 split 함수를 사용해
    폴더/도구 단위 파일로 분리하고 저장합니다.
    """

    # 1. JSON/YAML 블록 추출
    try:
        tool_spec_str_matched = re.search(r"```(json|yaml)\n(.*?)\n```", input_text, re.DOTALL)
        if tool_spec_str_matched is None:
            tool_spec_str = input_text
        else:
            tool_spec_str = tool_spec_str_matched.group(2).strip()
        res = yaml.safe_load(tool_spec_str)
    except Exception as e:
        raise ValueError(f'fails to extract output, error: {str(e)}, {input_text}')

    return res

class BaseValidator(ABC):
    """Validator base — ``llm_retry=False`` 는 NodeV 내부 루프만 건너뛴다.

    runner 는 같은 generate 에서 소스를 재생성한다. 사용자 재요청이 아니다.
    """

    llm_retry: bool = True

    def __init__(self):
        self.name = self.__class__.__name__
        try:
            # LLM이 분석할 수 있도록 자식 클래스의 validate 소스 코드를 추출
            self.source_code = inspect.getsource(self.validate).strip()
        except Exception:
            self.source_code = "Source code unavailable"

    @abstractmethod
    def validate(self, data: Any) -> Any:
        """
        검증 및 변환 로직.
        - 실패 시: Exception을 raise 하세요.
        - 성공 시: (변환된) 데이터를 return 하세요.
        """
        pass

class PydanticValidator(BaseValidator):
    """LLM 응답이 Pydantic 모델 스키마를 준수하는지만 검증"""

    def __init__(self, output_model: Type[BaseModel]):
        super().__init__()
        self.output_model = output_model

    def validate(self, data):
        resp_parsed = output_from_raw_response(data)
        current_data = self.output_model.model_validate(resp_parsed)
        return current_data

class NodeV:
    """Base node: Pydantic I/O, LLM codegen loop, validators, and validated.md learning."""
    __node_input_model__: Type[BaseModel]
    __node_output_model__: Type[BaseModel]
    __llm_types__: List[str]

    def __init__(self, validators: List[BaseValidator] = None, max_retries: int = 3):
        if not hasattr(self, '__node_input_model__'):
            raise TypeError(f"'{self.__class__.__name__}' 클래스는 @node 데코레이터로 정의되어야 합니다.")

        self.input_model = self.__node_input_model__
        self.output_model = self.__node_output_model__
        self.llm_types = self.__llm_types__
        # validators 체인: 항상 Pydantic 스키마 검증이 선두.
        # 이후 커스텀 validator 가 코드/의미 검증을 이어서 수행 (아래 run 루프).
        self.validators = [PydanticValidator(self.output_model)] + (validators or [])

        # 재시도 횟수 기본값 설정
        self.max_retries = max_retries

        node_impl = sys.modules.get(self.__class__.__module__)
        self.node_dir = Path(node_impl.__file__).resolve().parent

        try:
            # node_dir이 nodes_path 아래에 있는가?
            is_under_nodes = Path(self.node_dir).is_relative_to(cfg.nodes_path)
            self.is_embedded = not is_under_nodes
        except ValueError:
            # 서로 다른 드라이브거나 경로 계산이 불가능할 경우 (보통 하위가 아님)
            self.is_embedded = True

        if self.is_embedded:  # sage 패키지 내장 노드 — 파일 기반 instruction 없음
            # validated.md 를 쓰지 않음: 패키지 내부는 배포물로 취급, 학습 쓰기 금지.
            self.instruction = getattr(self, 'instruction', None)
            self.validated = None
        else:
            # nodes/{path}/ — LLM 프롬프트·학습 lesson 파일
            self.instruction = self.node_dir / "instruction.md"
            self.validated = self.node_dir / "validated.md"

        # self._ensure_node_files()

        self.llm_processors: Dict[str, Any] = {}
        for llm_type in self.llm_types:
            self.llm_processors[llm_type] = LLMFactory.get_llm(llm_type)

        model_name_snake = self._to_snake_case(self.output_model.__name__)
        self.model_prompt_path = pp.find_model_prompt(model_name_snake)

        self._cached_schema = None
        self.last_raw_response = ""  # 마지막 LLM 응답을 추적하기 위한 변수 추가

    def _get_output_schema_prompt(self) -> str:
        """출력 스키마 안내 — Gemini structured output 시 간략화."""
        if self._cached_schema is not None and isinstance(self._cached_schema, str):
            return self._cached_schema

        use_structured = (
            LLMFactory.DEFAULT_LLM_TYPE in ("gemini", "cursor")
            and isinstance(
                self.llm_processors.get(LLMFactory.DEFAULT_LLM_TYPE),
                (GeminiLLM, CursorLLM),
            )
        )
        if use_structured:
            guide = ""
            if self.model_prompt_path and self.model_prompt_path.exists():
                guide = self.model_prompt_path.read_text(encoding="utf-8").strip()
            self._cached_schema = (
                "### 출력 (JSON schema 강제)\n"
                "응답은 **단일 JSON 객체**만 반환됩니다. markdown 코드펜스·설명 문장 금지.\n"
                f"모델: `{self.output_model.__name__}`\n\n"
                f"{guide}\n"
            ).strip()
            return self._cached_schema

        schema = self.output_model.model_json_schema()

        if self.model_prompt_path and self.model_prompt_path.exists():
            external_guide = self.model_prompt_path.read_text(encoding="utf-8").strip()
            current_desc = schema.get("description", "")
            schema["description"] = f"{current_desc}\n\n{external_guide}".strip()

        self._cached_schema = (
            f"### 요청된 출력 YAML 스키마, 최종 응답은 반드시 아래 스키마(schema)를 지켜 응답하라\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n"
        )
        return self._cached_schema

    def _to_snake_case(self, name: str) -> str:
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    def _ensure_node_files(self):
        """노드 실행에 필요한 파일들이 없으면 빈 파일 생성"""
        self.node_dir.mkdir(parents=True, exist_ok=True)
        for p in [self.validated]:  # self.instruction
            if not p.exists():
                p.write_text("", encoding="utf-8")

    def _load_instruction_raw(self) -> str:
        inst = self.instruction
        if isinstance(inst, Path) and inst.exists():
            return inst.read_text(encoding="utf-8")
        if isinstance(inst, str) and "\n" not in inst and len(inst) < 260 and os.path.exists(inst):
            return Path(inst).read_text(encoding="utf-8")
        return inst if isinstance(inst, str) else ""

    def _node_path_key(self) -> str | None:
        if self.is_embedded:
            return None
        try:
            return str(self.node_dir.relative_to(cfg.nodes_path)).replace("\\", "/")
        except ValueError:
            return None

    # validated.md — instruction.md 가 최우선. 코드·JSON·stale import 오염 시 제거.
    _MAX_VALIDATED_CHARS = MAX_PROMPT_CHARS
    _MAX_VALIDATED_LINES = MAX_PROMPT_LINES
    _MAX_LESSON_CHARS = 800
    _MAX_LESSON_SECTIONS = 10

    def _instruction_resolved(self) -> str:
        base = self._load_instruction_raw()
        if not base:
            return ""
        return pp.resolve_pattern(base, current_dir=self.node_dir)

    def _validated_conflicts_with_instruction(self, validated_text: str) -> tuple[bool, str]:
        _, reasons = prepare_for_prompt(validated_text)
        if reasons:
            return True, "; ".join(reasons)
        return False, ""

    def _reconcile_validated_md(self) -> None:
        """오염·코드 블록 제거. 정화 불가 시 삭제."""
        if self.is_embedded or not self.validated:
            return
        path = Path(self.validated)
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        new_content, actions = reconcile_validated_file(text)
        for act in actions:
            warning(f"[NodeV] {path.name}: {act}")
        if new_content is None:
            path.unlink(missing_ok=True)
            return
        if new_content != text.strip():
            path.write_text(new_content + ("\n" if new_content else ""), encoding="utf-8")

    def _get_combined_instruction(self, *, focus_category: str | None = None) -> str:
        """instruction.md + validated.md + JSON Schema 결합."""
        # 1) instruction.md — 절대 규칙
        # 2) 출력 스키마
        # 3) validated.md — 보조; 재시도 시 focus_category lesson 우선
        # validator 재시도 피드백은 run() messages user tail 로 전달
        self._reconcile_validated_md()
        base = self._load_instruction_raw()
        sys_inst = pp.resolve_pattern(base, current_dir=self.node_dir)

        schema_prompt = self._get_output_schema_prompt()
        lesson_learned_prompt = self._get_lesson_learned(focus_category=focus_category)

        prompt = f"{sys_inst}\n\n{schema_prompt}\n\n{lesson_learned_prompt}"
        return prompt

    def _get_lesson_learned(self, *, focus_category: str | None = None) -> str:
        # 오염된 validated 는 프롬프트에 넣지 않음
        from sage.nodes.validated_md import extract_category_sections, load_report_task_shared_lessons

        self._reconcile_validated_md()
        lessons = ""
        focused = ""
        if self.validated and self.validated.exists():
            raw = self.validated.read_text(encoding="utf-8").strip()
            cleaned, reasons = prepare_for_prompt(raw)
            if reasons:
                warning(
                    f"[NodeV] validated.md skipped in prompt: {'; '.join(reasons)}"
                )
            else:
                lessons = cleaned
                if focus_category:
                    focused = extract_category_sections(raw, frozenset({focus_category}))
        shared = ""
        if self.node_dir:
            shared = load_report_task_shared_lessons(
                self.node_dir, frozenset({"UpstreamBoardValidator"})
            )
        if not lessons and not shared and not focused:
            return ""
        blocks: list[str] = []
        if focused:
            blocks.append(f"### 이번 validator ({focus_category}) 과거 lesson\n{focused}")
        if lessons:
            blocks.append(lessons)
        if shared:
            blocks.append(
                "## report task 공유 학습 (UpstreamBoardValidator)\n" + shared
            )
        body = "\n\n".join(blocks)
        return (
            "\n## 자주 하는 실수 (validated 학습 — instruction.md 보조, 코드·import 금지)\n"
            f"{body}"
        )

    def _ensure_lesson_accumulator(self) -> LessonAccumulator:
        acc = getattr(self, "_lesson_accumulator", None)
        if acc is None:
            acc = LessonAccumulator()
            self._lesson_accumulator = acc
        return acc

    def note_failure(
        self,
        category: str,
        error_msg: str,
        *,
        phase: str = "codegen",
        attempt: int = 1,
    ) -> None:
        """재시도 중 실패 축적 — flush_learned_lessons 전까지 validated.md 미기록."""
        # ------------------------------------------------------------------
        # note_failure vs flush_learned_lessons
        # - 재시도마다 파일을 쓰면 I/O·중복 lesson 이 폭발하고, 실패한 시도의
        #   noisy traceback 이 validated.md 에 쌓인다.
        # - 따라서 메모리 accumulator 에만 모았다가, 성공(resolved=True) 또는
        #   max retry 실패(resolved=False) 시 한 번에 consolidate → 기록.
        # - 외부 러너(보고서 태스크 등)가 실행 단계 실패를 알려줄 때도 사용.
        # ------------------------------------------------------------------
        if self.is_embedded:
            return
        self._ensure_lesson_accumulator().add(
            category, error_msg, phase=phase, attempt=attempt  # type: ignore[arg-type]
        )

    def flush_learned_lessons(self, *, resolved: bool = True) -> None:
        """축적된 실패를 validated.md 에 저장 (sync — async 컨텍스트 밖)."""
        coro = self._flush_lesson_accumulator_async(resolved=resolved)
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    async def flush_learned_lessons_async(self, *, resolved: bool = True) -> None:
        """축적된 실패 → validated.md (instruction.md + LLM reconcile)."""
        await self._flush_lesson_accumulator_async(resolved=resolved)

    def _ensure_signature_cache(self) -> set[str]:
        cache = getattr(self, "_lesson_signatures", None)
        if cache is None:
            cache = set()
            self._lesson_signatures = cache
        return cache

    def record_immediate_lesson(
        self,
        category: str,
        error_msg: str,
        *,
        phase: str = "execute",
    ) -> None:
        """실패 즉시 validated.md 반영 — sync wrapper."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.record_immediate_lesson_async(category, error_msg, phase=phase)
            )
        except RuntimeError:
            asyncio.run(
                self.record_immediate_lesson_async(category, error_msg, phase=phase)
            )

    async def record_immediate_lesson_async(
        self,
        category: str,
        error_msg: str,
        *,
        phase: str = "execute",
    ) -> None:
        """validator 오류 → instruction.md 와 함께 LLM 이 validated.md 정리."""
        if self.is_embedded:
            return
        core = compress_error_for_lesson(error_msg)
        sig = error_signature(core or error_msg)
        cache = self._ensure_signature_cache()
        if sig in cache:
            return
        cache.add(sig)
        lesson = format_structured_lesson(
            category, core or error_msg, phase=phase, resolved=False  # type: ignore[arg-type]
        )
        await self._record_lesson_async(
            category,
            normalize_lesson(lesson, error_msg=core or error_msg),
            error_msg=core or error_msg,
            resolved=False,
        )

    async def _flush_lesson_accumulator_async(self, *, resolved: bool) -> None:
        if self.is_embedded:
            return
        acc = getattr(self, "_lesson_accumulator", None)
        if not acc or not acc.has_events():
            return
        for category, error_msg, phase in consolidate_events(acc.events):
            core = compress_error_for_lesson(error_msg)
            lesson = format_structured_lesson(
                category, core or error_msg, phase=phase, resolved=resolved
            )
            await self._record_lesson_async(
                category,
                normalize_lesson(lesson, error_msg=core or error_msg),
                error_msg=core or error_msg,
                resolved=resolved,
            )
        self._lesson_accumulator = LessonAccumulator()

    def _flush_lesson_accumulator(self, *, resolved: bool) -> None:
        """내부 legacy — flush_learned_lessons_async 사용."""
        coro = self._flush_lesson_accumulator_async(resolved=resolved)
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def _prune_lesson_sections(self, lines: list[str]) -> list[str]:
        """오래된 ## [category] 섹션 상한."""
        headers = [i for i, line in enumerate(lines) if line.startswith("## [")]
        if len(headers) <= self._MAX_LESSON_SECTIONS:
            return lines
        drop_until = headers[-(self._MAX_LESSON_SECTIONS)]
        return lines[drop_until:]

    async def _record_lesson_async(
        self,
        category: str,
        lesson: str,
        *,
        error_msg: str = "",
        resolved: bool = False,
    ) -> None:
        """Validator lesson → validated.md (instruction.md + LLM reconcile)."""
        if self.is_embedded:
            return

        lesson = normalize_lesson(lesson or "", error_msg=error_msg)
        if not lesson:
            return
        if len(lesson) > self._MAX_LESSON_CHARS:
            lesson = lesson[: self._MAX_LESSON_CHARS] + "\n...(truncated; see instruction.md)"

        if not is_lesson_saveable(lesson):
            warning(
                f"[NodeV] lesson not saved ({category}): polluted content "
                "(code/json/stale import/forbidden advice)"
            )
            return

        self._reconcile_validated_md()
        self._ensure_node_files()

        path = Path(self.validated)
        header = "# SAG-E Self-Healing Lessons (Validated Knowledge)\n"
        header_note = (
            "# instruction.md 가 최우선. 본 파일은 **bullet 요약만** — "
            "code/json/import/run_task 템플릿 저장 금지.\n"
        )

        content_lines: list[str] = []
        if path.exists():
            content_lines = path.read_text(encoding="utf-8").splitlines()
        else:
            content_lines = [header.strip(), header_note.strip()]

        start_tag = f"## [{category}]"
        new_lines: list[str] = []
        skip = False

        for line in content_lines:
            if skip and line.startswith("## [") and not line.startswith(start_tag):
                skip = False
            if line.startswith(start_tag):
                skip = True
                continue
            if not skip and line.strip():
                new_lines.append(line)

        new_lines = self._prune_lesson_sections(new_lines)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lesson_entry = [
            "",
            start_tag,
            f"- **최근 업데이트**: {timestamp}",
            lesson.strip(),
            "---",
        ]

        draft_content = "\n".join(new_lines + lesson_entry)
        instruction = self._instruction_resolved()
        reconciled = await llm_reconcile_validated_md(
            instruction=instruction,
            draft_validated=draft_content,
            category=category,
            error_msg=error_msg or lesson,
            resolved=resolved,
        )
        final_content = reconciled if reconciled else draft_content
        final_content, _ = reconcile_validated_file(final_content)
        if final_content is None:
            warning(f"[NodeV] validated.md not updated ({category}): polluted merged content")
            return

        path.write_text(final_content, encoding="utf-8")
        if reconciled:
            debug(f"[NodeV] validated.md LLM-reconciled with instruction.md ({category})")

    async def lesson_exception(self, e: Exception):
        """런타임 오류 → 구조화 lesson (LLM reflection 없이 validated.md 기록)."""
        # pangeaze unify 실패처럼 NodeV.run 바깥에서 난 오류도 학습에 넣고 싶을 때.
        error_msg = str(e)
        category = infer_lesson_category(error_msg)
        self._ensure_node_files()
        lesson = format_structured_lesson(
            category, error_msg, phase="runtime", resolved=True
        )
        await self._record_lesson_async(
            category, normalize_lesson(lesson, error_msg=error_msg), error_msg=error_msg, resolved=True
        )

    def _get_input_prompt(self, **kwargs) -> str:
        """Input 필드 + enrich 추가 필드를 LLM user prompt 로 변환."""
        from sage.prompt.enrich import llm_prompt_fields

        parts = llm_prompt_fields(kwargs, self.input_model)
        return "\n\n".join(f"### {label} ({name})\n{val}" for name, label, val in parts)

    async def run(self, **kwargs) -> Type[BaseModel]:
        """Execute the LLM codegen loop with validation and self-healing retries.

        Args:
            **kwargs: Validated against the node's ``@node`` input model.
            _retry_sink: Optional list to collect retry telemetry (internal).
            _lesson_flush: When False, defer validated.md writes (internal).

        Returns:
            Validated output model instance.

        Raises:
            MaxRetriesExceededError: All retry attempts failed validation.
        """
        # ==================================================================
        # NodeV.run 루프 스테이지
        # 0) kwargs 정리 / lesson accumulator 초기화
        # 1) 입력 Pydantic 검증
        # 2) enrich — 스키마·도구 명세 등 파생 컨텍스트를 kwargs 에 주입
        # 3) combined instruction + user prompt 조립
        # 4) for attempt in max_retries:
        #      a. LLM generate (system/user + 이전 실패 feedback)
        #      b. validators 체인 순회 (변환 파이프: 출력이 다음 입력)
        #      c. 실패 → accumulator + last_error_feedback, 다음 attempt
        #      d. 성공 → flush(resolved=True) 후 return
        # 5) 전부 실패 → flush(resolved=False) + MaxRetriesExceededError
        # "Full rollback": 부분 성공 상태를 유지하지 않고 매 시도 raw 부터 재검증.
        # ==================================================================
        retry_sink = kwargs.pop("_retry_sink", None)
        lesson_flush = kwargs.pop("_lesson_flush", True)
        if lesson_flush:
            # 호출 단위로 accumulator 리셋 — 이전 run 의 실패가 섞이지 않게.
            self._lesson_accumulator = LessonAccumulator()
        else:
            # 상위가 여러 run 을 묶을 때(_lesson_flush=False) 누적만 하고
            # 쓰기는 상위 flush_learned_lessons 에 위임.
            self._ensure_lesson_accumulator()

        def _notify_retry(attempt: int, error: str, kind: str) -> None:
            if retry_sink is None:
                return
            retry_sink(
                attempt=attempt,
                max_attempts=self.max_retries,
                error=error,
                kind=kind,
            )

        # --- Stage 1: 입력 유효성 검사 ---
        # try:
        self.input_model(**kwargs)  # raise ValidationError
        # except ValidationError as e:
        #     raise ValueError(f"입력 데이터 검증 오류: {e}")

        # --- Stage 2: enrich ---
        # 입력 모델 Field/메타에 선언된 enrich 훅을 실행해 LLM 이 필요로 하는
        # 부가 컨텍스트(예: 데이터셋 스키마)를 kwargs 에 채움.
        from sage.prompt.enrich import apply_enrich

        kwargs = await apply_enrich(kwargs, self.input_model)

        last_error_feedback = ""
        last_validator_category = ""
        last_validator_error = ""
        input_content = self._get_input_prompt(**kwargs)

        # --- Stage 3–4: 자가 치유 루프 ---
        node_path = self._node_path_key()
        llm_processor = self.llm_processors[LLMFactory.DEFAULT_LLM_TYPE]
        llm_type = LLMFactory.DEFAULT_LLM_TYPE
        llm_model = getattr(llm_processor, "model_name", llm_type)
        task_type = kwargs.get("type")

        for attempt in range(self.max_retries):
            focus = last_validator_category or None
            base_instruction = self._get_combined_instruction(focus_category=focus)
            instruction_content = base_instruction
            if last_validator_error:
                instruction_content = (
                    format_validator_system_priority_block(
                        last_validator_category,
                        last_validator_error,
                        attempt=attempt,
                    )
                    + base_instruction
                )
            user_content = input_content
            if last_error_feedback:
                retry_cat = last_validator_category or infer_lesson_category(last_error_feedback)
                retry_err = last_validator_error or last_error_feedback
                user_content = (
                    f"{input_content}\n\n"
                    "## validator 수정 요청 (user — 최우선)\n"
                    f"{format_validator_retry_user_block(retry_cat, retry_err, attempt=attempt)}"
                )
            log_prompt_before_llm(
                node_path=node_path,
                attempt=attempt,
                llm_type=llm_type,
                model=llm_model,
                task_type=str(task_type) if task_type else None,
                system=instruction_content,
                user=user_content,
                feedback=last_error_feedback,
                attach=kwargs.get("llm_attach"),
                extra_messages=0,
            )

            messages = [
                Message(role='system', content=instruction_content),
                Message(role='user', content=user_content)
            ]

            try:
                processor = llm_processor
                gen_kwargs: dict[str, Any] = {}
                if isinstance(processor, (GeminiLLM, CursorLLM)):
                    # structured output: JSON Schema 강제 → 파싱 실패율 감소.
                    gen_kwargs["response_model"] = self.output_model

                self.last_raw_response = await processor.generate_async(
                    messages,
                    attach=kwargs.get("llm_attach"),
                    **gen_kwargs,
                )

                if not self.last_raw_response:
                    warning("LLM 응답이 비어있습니다.")
                    continue

                current_data = self.last_raw_response
                error_trapped = False

                # --- validators 체인 ---
                # 각 validator 는 입력을 검증·변환해 다음으로 넘김.
                # 예: PydanticValidator(raw→모델) → CodeValidator(모델.code 실행) …
                # 중간에 하나라도 실패하면 그 validator.name 으로 lesson/feedback 생성.
                for validator in self.validators:
                    try:
                        # 검증 실행
                        current_data = validator.validate(current_data)
                    except Exception as e:
                        error_msg = str(e)
                        category = validator.name
                        core = compress_error_for_lesson(error_msg)
                        warning(
                            f"![{self.__class__.__name__}] codegen "
                            f"{attempt + 1}/{self.max_retries} {category} 실패:\n"
                            f"{core or error_msg}"
                        )
                        llm_retry = getattr(validator, "llm_retry", True)
                        if not llm_retry:
                            await self.record_immediate_lesson_async(
                                category, error_msg, phase="codegen"
                            )
                            msg = format_record_only_feedback(category, error_msg)
                            _notify_retry(attempt + 1, msg, "validator_record_only")
                            raise CodegenContractError(msg, category=category) from e
                        self._lesson_accumulator.add(
                            category,
                            error_msg,
                            phase="codegen",
                            attempt=attempt + 1,
                        )
                        last_validator_category = category
                        last_validator_error = error_msg
                        last_error_feedback = format_retry_feedback(
                            category, error_msg, attempt=attempt + 1
                        )
                        _notify_retry(attempt + 1, error_msg, "validator")

                        error_trapped = True
                        break

                if not error_trapped:
                    # 성공 시 그동안의 실패 패턴을 "해결된 lesson" 으로 남김.
                    if lesson_flush and self._lesson_accumulator.has_events():
                        await self._flush_lesson_accumulator_async(resolved=True)
                    return current_data

            # except ServerError as e:
            #     status = getattr(e, 'status_code', None)
            #     if status == 503 or "503" in str(e) or "UNAVAILABLE" in str(e):
            #         warning(f"Gemini 서버 과부하(503). 잠시 후 재시도합니다.")
            #         time.sleep(5)
            #         continue
            #     continue

            except (ServiceUnavailableError, QuotaExceededError, LLMTimeoutError, ContextAttachTooLargeError):
                # 인프라/쿼터/컨텍스트 한도는 재시도로 해결 불가 — 즉시 상위로.
                raise
            except (ConnectionResetError, BrokenPipeError) as e:
                # 10054 에러 등 네트워크 단절은 인프라 문제로 간주
                warning(f"네트워크 일시 단절: {e}. 5초 대기 후 재시도합니다.")
                await asyncio.sleep(5)
                continue  # validation.md 기록 없이 다시 루프 시작

            except Exception as e:
                if is_quota_error(e):
                    raise QuotaExceededError() from e
                error_msg = f"실행 중 예외 발생: {e}\n{traceback.format_exc()}"
                self._lesson_accumulator.add(
                    infer_lesson_category(error_msg),
                    error_msg,
                    phase="codegen",
                    attempt=attempt + 1,
                )
                last_error_feedback = error_msg
                warning(f"![{self.__class__.__name__}] Attempt {attempt + 1} Error: {last_error_feedback}")
                _notify_retry(attempt + 1, last_error_feedback, "runtime")
                continue

        # --- Stage 5: 최종 실패 ---
        if lesson_flush:
            await self._flush_lesson_accumulator_async(resolved=False)
        final_error = last_validator_error or last_error_feedback
        error(
            f"![{self.__class__.__name__}] 최대 재시도({self.max_retries}) 초과:\n"
            f"{compress_error_for_lesson(final_error) or final_error}"
        )
        raise MaxRetriesExceededError(self.max_retries, last_error=final_error)

    async def __call__(self, **kwargs) -> Type[BaseModel]:
        return await self.run(**kwargs)

@node(input=ToolErr, output=ToolPack)
class ToolFix(NodeV):
    """에러 분석 및 수정 전문"""

    instruction = """오류를 고친 ToolPack 전체를 다시 작성하라.

[[tool/tool_pack]]
[[tool/secret_usage]]
"""

    def __init__(self, validators: List[BaseValidator] = None, max_retries: int = 3):
        super().__init__(
            validators=[_SourceFixCallerValidator()] + (validators or []),
            max_retries=max_retries,
        )

class _SourceFixCallerValidator(BaseValidator):
    """SourceFixed.fixed_code / ToolPack.caller 에 docker caller 계약 적용."""

    def validate(self, data: Any):
        from sage.tool.caller_contract import assert_caller_mcp_import, caller_source_of

        src = caller_source_of(data)
        if not src.strip():
            return data
        assert_caller_mcp_import(src)
        return data


class _SourceUnchangedValidator(BaseValidator):
    """원본과 동일한 fixed_code 는 오류를 무시한 것 — LLM 에 명시적으로 재요청."""

    def __init__(self):
        super().__init__()
        self.original = ""

    def validate(self, data: Any):
        from sage.tool.caller_contract import caller_source_normalized

        src = getattr(data, "fixed_code", "") or ""
        if self.original and caller_source_normalized(src) == caller_source_normalized(
            self.original
        ):
            raise ValueError(
                "계약 위반: fixed_code 가 오류 난 원본과 동일하다. "
                "error 필드의 원인을 반영해 고쳐라. 원본 복붙 금지."
            )
        return data


@node(input=SourceErr, output=SourceFixed)
class SourceFix(NodeV):
    """도구 외 caller 소스 오류 수정 전문"""

    instruction = """caller.py 만 고친다. error 를 반영하라.

[[tool/caller_api]]
"""

    def __init__(self, validators: List[BaseValidator] = None, max_retries: int = 3):
        self._unchanged = _SourceUnchangedValidator()
        extra = [_SourceFixCallerValidator(), self._unchanged]
        super().__init__(validators=extra + (validators or []), max_retries=max_retries)

    async def run(self, **kwargs):
        self._unchanged.original = kwargs.get("code") or ""
        return await super().run(**kwargs)
