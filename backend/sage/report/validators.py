"""p2 report NodeV codegen validators — LLM 출력 사전 검증.

파이프라인 개요
---------------
report 파이프라인에서 LLM 이 생성한 executor(`async def run_task`) / plan JSON 을
**실행 전**에 정적 검사한다. 런타임 NameError·잘못된 MCP 호출·가짜 데이터 하드코딩을
재시도 루프 안에서 빠르게 거르기 위한 계층이다.

검증 진입점 (호출 순서):
1. ``task_validators_for(task_type)`` — 공통 + 타입별 validator 인스턴스 조립
2. ``configure_task_validators(...)`` — MCP allow-list, Pangea model/schema, TaskContext
   칠판(board) 등 *런타임 의존* 상태를 validator 에 주입
3. 각 ``BaseValidator.validate(data)`` — ``data.code``(또는 ReportPlanOutput) 검사

보조 진입점:
- ``validate_codegen_output`` — NodeV(codegen) 직후 풀 스위트 (configure 포함)
- ``run_task_code_validators`` — 디스크 저장 직전 최소 검증 (board/MCP 없이 동작)
- ``PlanStructureValidator`` — plan DAG·tools 일관성 (코드가 아닌 ReportPlanOutput)

공통 suite(_COMMON_VALIDATORS): 문법 → import → run_task 구조 → anti-pattern →
MCP call → UpstreamBoard. 타입별(_TYPE_VALIDATORS)이 그 뒤에 붙는다.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Iterable

import cfg

from sage.report.codegen_contract import (
    FORBIDDEN_PATTERNS,
    PROGRESS_JARGON_RE,
    PROGRESS_MSG_RE,
)
from sage.models.node import ReportPlanOutput
from sage.report.plan_tools import resolve_task_tool_paths
from sage.nodes import BaseValidator
from sage.data.schema_contract import SchemaContractError
from sage.report.schema_contract import validate_codegen_schema_contract
from sage.report.context_keys import (
    NARRATIVE_DRAFT_KEY,
    RELEASE_REPORT_KEY,
    RELEASE_REPORT_KEYS,
    RELEASE_SUMMARY_KEY,
)
from sage.report.runner import topo_sort_tasks
from sage.report.task_shell import assert_assembled, assert_no_imports

def _code(data: Any) -> str:
    """TaskOutput / 어댑터 객체에서 code 문자열 추출 — validator 공통 전제."""
    code = getattr(data, "code", None)
    if not code:
        raise ValueError("TaskOutput.code 가 비어 있습니다.")
    return code

def _parse(code: str) -> ast.Module:
    """ast.parse 래퍼 — SyntaxError 시 upstream embed 힌트."""
    try:
        return ast.parse(code)
    except SyntaxError as exc:
        from sage.report.task_shell import codegen_syntax_hint

        hint = codegen_syntax_hint(code)
        if hint:
            raise ValueError(f"{exc.msg} — {hint}") from exc
        raise


# ---------------------------------------------------------------------------
# Regex ban helpers — analyze/visual/narrative 가 공유하는 "칠판/데이터 접근" 규칙
#
# 왜 regex 인가: executor 는 LLM 이 매 시도마다 새로 쓰므로 AST 전체 흐름분석보다
# 자주 틀리는 anti-pattern 문자열을 빠르게 거부하는 편이 재시도 UX 에 유리하다.
# 허용 경계가 느슨하면(오탐) codegen 이 막히고, 너무 타이트하면 런타임에서 터진다.
# ---------------------------------------------------------------------------

def _check_ctx_data_access(code: str) -> None:
    """Ban get_result key-probing and empty DataFrame fallbacks (all non-data tasks).

    차단하는 4가지 패턴과 배경:
    1) ``get_result('task-...')`` — task_id 리터럴. context 가 DAG 로 바뀔 때
       깨지므로 ``task.context[i]`` 변수만 허용.
    2) ``for x in [..]: get_result(...)`` — key 후보를 루프로 찔러보는 탐색.
       칠판(catalog)에 이미 확정된 key 를 1회 호출해야 한다.
    3) ``get_result(...) try/except continue`` — 실패를 삼키며 다음 key 시도.
       데이터 부재를 성공으로 위장하는 대표 패턴.
    4) ``pd.DataFrame(columns=...)`` — 빈 DF fallback. 다운스트림이 빈 표를
       "정상 결과"로 렌더링하는 사고를 막기 위해 명시적 raise 를 강제.
    """
    if re.search(r"""get_result\s*\(\s*['"]task-""", code):
        raise ValueError(
            "get_result(task_id, key) 에 task_id 문자열 하드코딩 금지 — "
            "task.context[i] 또는 task.context 를 순회한 변수 사용"
        )
    if re.search(
        r"for\s+\w+\s+in\s*\[[^\]]+\][\s\S]{0,600}?get_result\s*\(",
        code,
    ):
        raise ValueError(
            "ctx.get_result key 탐색 loop 금지 — "
            "칠판 task_id·key 를 1개씩 고정 호출. "
            "통합 원본: PangeaExDataFrame(did=task.data_id).to_pandas(model) "
            "(dataset_context [PANGEA TARGETS])"
        )
    if re.search(
        r"get_result\s*\([^)]*\)[\s\S]{0,150}?except\b[\s\S]{0,80}?continue\b",
        code,
    ):
        raise ValueError(
            "get_result try/except continue 금지 — key·task_id 는 칠판에서 확정 후 1회 호출"
        )
    if re.search(r"pd\.DataFrame\s*\(\s*columns\s*=", code):
        raise ValueError(
            "빈 pd.DataFrame(columns=...) fallback 금지 — "
            "PangeaExDataFrame 또는 칠판 get_result, 없으면 raise"
        )

def _check_pangea_to_pandas(code: str) -> None:
    """PangeaExDataFrame 만 만들고 to_pandas 를 빼먹는 케이스 차단.

    ExDataFrame 자체는 lazy/브리지 객체라 model 인자 없는 채로 내려가면
    다운스트림에서 스키마·컬럼이 확정되지 않는다. model 은 metadata
    targets[].model(= dataset_context [PANGEA TARGETS]) 과 일치해야 한다.
    """
    if re.search(r"PangeaExDataFrame\s*\(", code) and "to_pandas(" not in code:
        raise ValueError(
            "PangeaExDataFrame 사용 시 to_pandas(model) 필수 — "
            "model 은 dataset_context [PANGEA TARGETS] 만 (proto:pangea_api)"
        )

async def build_mcp_call_specs(
    tools: list[str] | None,
    *,
    data_id: str | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """(tool_path, name) → tools spec input schema.

    ``tools_spec_for_llm`` 이 경로별로 JSON 문자열 블록을 돌려주므로, 여기서
    (tool_path, name) 키로 평탄화한다. McpCallValidator 가 call() AST 와
    대조할 allow-list / input.properties 의 원천이다.
    JSON 파싱 실패 블록은 skip — 한 path 스펙이 깨져도 다른 path 검증은 유지.
    """
    from sage.prompt.enrich import tools_spec_for_llm

    out: dict[tuple[str, str], dict[str, Any]] = {}
    specs = await tools_spec_for_llm(list(tools or []), data_id=data_id)
    for block in specs:
        try:
            for tool in json.loads(block):
                path = tool.get("tool_path", "")
                name = tool.get("name", "")
                if path and name:
                    out[(path, name)] = tool.get("input") or {}
        except json.JSONDecodeError:
            continue
    return out


async def configure_mcp_validator(
    validators: Iterable[BaseValidator], kwargs: dict[str, Any]
) -> None:
    """McpCallValidator — tools spec → call allow-list / input schema 주입."""
    call_specs = await build_mcp_call_specs(
        list(kwargs.get("tools") or []),
        data_id=kwargs.get("data_id"),
    )
    for validator in validators:
        if isinstance(validator, McpCallValidator):
            validator.allowed_calls = set(call_specs.keys())
            validator.call_specs = call_specs


class UpstreamBoardValidator(BaseValidator):
    """analyze/visual/narrative — 칠판에 없는 get_result key·task_id 차단.

    왜 필요한가
    -----------
    선행 태스크가 ``ctx.update_task(key=...)`` 로 남긴 산출물만 downstream 이
    ``get_result`` 로 읽을 수 있다. LLM 은 prompt 예시 key 를 그대로 베끼는
    경향이 있어, 칠판(catalog)에 없는 key 를 호출하면 실행 시 None/KeyError 로
    실패한다. 이 validator 는 codegen 단계에서 key 리터럴을 board 와 교차검증한다.

    데이터 흐름
    -----------
    - ``configure_task_validators`` 가 ``TaskContext.catalog()`` → ``self.board``,
      task.context → ``self.context`` 주입.
    - ``self.context`` 가 있으면 그 task_id 들의 keys 만 허용집합; 없으면 board
      전체 keys (context 미주입 경로 / 광범위 검증).
    - board 비어 있으면 skip — plan/codegen 초기에 선행 실행이 없을 수 있음.
    - context 는 있으나 keys 가 비면 에러: 선행이 아직 저장되지 않았거나
      llm_attach payload 를 쓰지 않은 상태.

    edge case: key 리터럴만 regex 로 뽑는다. 변수로 넘긴 key 는 정적 검사가
    불가능하므로 허용(런타임·Upstream 데이터에 위임).
    """

    board: dict[str, Any] = {}
    context: list[str] = []

    def validate(self, data: Any):
        code = _code(data)
        if not self.board:
            return data

        upstream_ids = list(self.context) if self.context else list(self.board.keys())
        allowed_keys: set[str] = set()
        for tid in upstream_ids:
            info = self.board.get(tid) or {}
            allowed_keys.update((info.get("keys") or {}).keys())

        if upstream_ids and self.board and not allowed_keys:
            raise ValueError(
                "upstream context 가 있으나 칠판에 등록된 key 가 없음 — "
                "선행 태스크 실행·저장 후 codegen 하거나 llm_attach payload key 사용"
            )

        for match in re.finditer(r"""get_result\s*\([^,]+,\s*['"]([^'"]+)['"]\s*\)""", code):
            key = match.group(1)
            if allowed_keys and key not in allowed_keys:
                raise ValueError(
                    f"get_result key {key!r} 가 upstream 칠판에 없음. "
                    f"허용 key: {sorted(allowed_keys)} — llm_attach upstream_payloads 참고"
                )
        return data


async def configure_task_validators(validators: Iterable[BaseValidator], kwargs: dict[str, Any]) -> None:
    """codegen validator — tools·task type 에 따른 런타임 주입.

    validate() 자체는 순수 코드 검사이지만, 허용집합은 *현재 plan/dataset 상태*에
    달려 있다. 이 함수가 그 상태를 읽어 각 validator 필드에 심는다.

    주입 매핑
    ---------
    - McpCallValidator ← ``configure_mcp_validator`` (tools → call allow-list)
    - DataTaskFlowValidator.requires_mcp ← data 타입이고 effective tools 가 있을 때만
      True. 파일소스만 있는 데이터셋은 MCP 없이 Pangea 로드만으로도 통과 가능.
    - DataTaskFlowValidator.allowed_models ← metadata.json targets[].model
    - SchemaContractValidator.schema_fields ← schema.py 파싱 결과
    - UpstreamBoardValidator ← TaskContext.catalog() + kwargs['context']

    data 타입일 때 ``resolve_task_tool_paths(..., task_type="data")`` 로 tools 를
    정규화하는 이유: plan 이 빈 tools 를 줘도 data_id 기준 기본 툴 path 가
    붙을 수 있어 requires_mcp / MCP 스펙과 일치시켜야 한다.
    """
    await configure_mcp_validator(validators, kwargs)
    tools = list(kwargs.get("tools") or [])
    task_type = kwargs.get("type")
    data_id = kwargs.get("data_id")
    effective_tools = (
        resolve_task_tool_paths(None, tools, task_type="data", data_id=data_id)
        if task_type == "data"
        else tools
    )
    allowed_models = load_pangea_models(data_id) if data_id else set()
    schema_fields = load_pangea_schema_fields(data_id) if data_id else {}

    board: dict[str, Any] = {}
    plan_id = kwargs.get("plan_id")
    if plan_id:
        from sage.report.context import TaskContext

        task_ctx = TaskContext.load(plan_id, rid=kwargs.get("rid"))
        board = task_ctx.catalog()

    for validator in validators:
        if isinstance(validator, DataTaskFlowValidator):
            validator.requires_mcp = bool(effective_tools) and task_type == "data"
            validator.allowed_models = allowed_models or None
        if isinstance(validator, SchemaContractValidator):
            validator.schema_fields = schema_fields
        if isinstance(validator, UpstreamBoardValidator):
            validator.board = board
            validator.context = list(kwargs.get("context") or [])

def _dict_literal_str_keys(node: ast.Dict) -> set[str]:
    keys: set[str] = set()
    for key_node in node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            keys.add(key_node.value)
    return keys


_UPDATE_TASK_RESERVED = frozenset(
    {"key", "value", "data_type", "description", "status", "results"}
)


def _update_task_keys(code: str) -> set[str]:
    """``ctx.update_task`` 에 등록되는 칠판 key — ``key=`` 및 kwargs payload 모두."""
    tree = _parse(code)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "update_task"):
            continue
        for kw in node.keywords:
            if not kw.arg:
                continue
            if kw.arg == "key":
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    keys.add(kw.value.value)
            elif kw.arg not in _UPDATE_TASK_RESERVED:
                keys.add(kw.arg)
        if len(node.args) >= 2:
            key_arg = node.args[1]
            if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
                keys.add(key_arg.value)
    return keys

def _detect_hardcoded_data_records(code: str) -> list[str]:
    """AST — 재무/시세 dict list literals (MCP 없이 박아 넣는 패턴).

    LLM 이 MCP 실패를 우회하려고 ``[{"ticker":..., "company_name":...}, ...]``
    같은 레코드를 소스에 박아 넣는 경우를 잡는다.
    - 재무: ticker+company_name / ticker+market_cap 키가 1행만 있어도 충분(오탐보다
      누락이 위험 — 한 종목이라도 하드코딩이면 파이프라인 왜곡).
    - 시세: ticker+close/open 은 2행 이상일 때만 — 단일 dict 예시는 false positive.
    """
    tree = _parse(code)
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        fin_rows = 0
        price_rows = 0
        flow_rows = 0
        for elt in node.elts:
            if not isinstance(elt, ast.Dict):
                continue
            keys = _dict_literal_str_keys(elt)
            if {"ticker", "company_name"} <= keys or {"ticker", "market_cap"} <= keys:
                fin_rows += 1
            if {"ticker", "close_price"} <= keys or {"ticker", "open_price"} <= keys:
                price_rows += 1
            if (
                {"sector_name", "foreign_buy"} <= keys
                or {"sector_name", "foreign_net_buy"} <= keys
                or {"sector_large", "foreign_net_buy"} <= keys
                or {"sector_medium", "institution_net_buy"} <= keys
            ):
                flow_rows += 1
        line = getattr(node, "lineno", 0)
        if fin_rows >= 1:
            issues.append(f"L{line}: 재무/종목 dict 하드코딩 {fin_rows}건")
        if price_rows >= 2:
            issues.append(f"L{line}: 시세 dict 하드코딩 {price_rows}건")
        if flow_rows >= 2:
            issues.append(f"L{line}: 업종 수급 dict 하드코딩 {flow_rows}건")
    return issues

def load_pangea_models(data_id: str, version: str = "v1") -> set[str]:
    meta_path = Path(cfg.root_path) / "data" / data_id / "pangea" / version / "metadata.json"
    if not meta_path.is_file():
        return set()
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return {t["model"] for t in metadata.get("targets", []) if t.get("model")}


def load_pangea_schema_fields(data_id: str, version: str = "v1") -> dict[str, dict[str, str]]:
    """{model: {field: canonical_type}} — codegen schema 검증용."""
    from sage.data.schema_types import parse_schema_field_types

    schema_path = Path(cfg.root_path) / "data" / data_id / "pangea" / version / "schema.py"
    if not schema_path.is_file():
        return {}
    return parse_schema_field_types(schema_path)

# Pangea API 호출부 첫 인자(model 문자열 리터럴) 추출.
# 동적 변수 model 은 잡지 않음 — 정적 상수 오타/환각만 사전 차단.
_PANGEA_MODEL_API_RE = re.compile(
    r"(?:to_pandas|plan_updates|queue_update|apply_pending_updates)\s*\(\s*([\"'])([^\"']+)\1"
)

def _detect_invalid_model_literals(code: str, allowed: set[str]) -> list[str]:
    """Pangea API 에 넘긴 model 문자열이 metadata targets[].model 인지.

    허용 집합이 비어 있으면 호출측에서 이 검사를 skip 한다(데이터셋 미준비).
    """
    issues: list[str] = []
    seen: set[str] = set()
    for match in _PANGEA_MODEL_API_RE.finditer(code):
        model = match.group(2)
        if model in seen or model in allowed:
            continue
        seen.add(model)
        issues.append(
            f"model {model!r} — metadata targets[].model 아님 (허용: {sorted(allowed)})"
        )
    return issues

# data 태스크 전용 — MCP 결과를 가짜로 합성할 때 반복되는 휴리스틱.
# (튜토리얼식 kospi_N_*, price*0.xx OHLCV 조작, range(N) 행 생성, 삼성전자 예시 티커)
_FAKE_DATA_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"kospi_\d+_(?:schema|prices|tickers)\s*=", "kospi_N_* 하드코딩 변수명"),
    (r"price\s*\*\s*0\.\d+", "가짜 OHLCV (price * ratio)"),
    (r"for\s+\w+\s+in\s+range\s*\(\s*[1-9]\d?\s*\)", "range(N) 고정 루프로 rows 생성"),
    (r'"005930"[\s\S]{0,120}"삼성전자"|"삼성전자"[\s\S]{0,120}"005930"', "티커·종목명 literals"),
)

def _detect_fake_data_patterns(code: str) -> list[str]:
    """_FAKE_DATA_PATTERNS 정규식 매칭 — DataTaskFlowValidator(requires_mcp) 에서만 사용."""
    issues: list[str] = []
    for pattern, msg in _FAKE_DATA_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(msg)
    return issues

def _dict_literal_keys(node: ast.expr | None) -> set[str] | None:
    """dict literal 의 상수 key 집합 — 동적 dict 는 None.

    McpCallValidator 가 call(..., {..}) 의 properties/required 를 대조할 때 사용.
    key 가 표현식(변수)이면 None 을 반환해 'args 키 검사는 skip, (path,name) 매칭만'.
    """
    if not isinstance(node, ast.Dict):
        return None
    keys: set[str] = set()
    for key_node in node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            keys.add(key_node.value)
        else:
            return None
    return keys

def _call_from_keywords(keywords: list[ast.keyword]) -> tuple[str | None, str | None, set[str] | None]:
    """call(path=, tool_name=, tool_args=) — positional 과 동일 검증."""
    path: str | None = None
    name: str | None = None
    arg_keys: set[str] | None = None
    for kw in keywords:
        if not kw.arg:
            continue
        if kw.arg in ("path", "tool_path") and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                path = kw.value.value
        elif kw.arg in ("tool_name", "name") and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                name = kw.value.value
        elif kw.arg in ("tool_args", "args", "arguments") and isinstance(kw.value, ast.Dict):
            arg_keys = _dict_literal_keys(kw.value)
    if path and name:
        return path, name, arg_keys
    return None, None, None


def _iter_calls(code: str) -> list[tuple[str, str, set[str] | None, int]]:
    """call(tool_path, name, args?) — positional·keyword 모두 수집."""
    tree = _parse(code)
    found: list[tuple[str, str, set[str] | None, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_call = (
            (isinstance(func, ast.Name) and func.id == "call")
            or (isinstance(func, ast.Attribute) and func.attr == "call")
        )
        if not is_call:
            continue
        lineno = getattr(node, "lineno", 0)
        if len(node.args) >= 2:
            path_arg, name_arg = node.args[0], node.args[1]
            if isinstance(path_arg, ast.Constant) and isinstance(name_arg, ast.Constant):
                if isinstance(path_arg.value, str) and isinstance(name_arg.value, str):
                    arg_keys = _dict_literal_keys(node.args[2]) if len(node.args) >= 3 else set()
                    found.append((path_arg.value, name_arg.value, arg_keys, lineno))
                    continue
        path, name, arg_keys = _call_from_keywords(node.keywords)
        if path and name:
            found.append((path, name, arg_keys, lineno))
    return found

class TaskCodeSyntaxValidator(BaseValidator):
    """생성 executor Python 문법 검증 — suite 최전방. AST 파싱 실패를 즉시 거른다."""

    def validate(self, data: Any):
        _parse(_code(data))
        return data


class LlmImportForbiddenValidator(BaseValidator):
    """LLM executor body — import 금지 (prelude 가 주입)."""

    def validate(self, data: Any):
        assert_no_imports(_code(data), where="LLM executor")
        return data


class AssembledSourceValidator(BaseValidator):
    """디스크 저장본 — 표준 prelude + body import 금지."""

    def validate(self, data: Any):
        assert_assembled(_code(data))
        return data


class RunTaskStructureValidator(BaseValidator):
    """run_task 시그니처·TaskContext 저장 패턴.

    runner 는 ``async def run_task(task, ctx, reporter=None)`` 만 await 한다.
    동기 def 나 함수 누락은 즉시 실패. update_task + save 한 쌍이 없으면
    칠판에 남지 않아 downstream 이 빈 board 를 보게 되므로 강제한다.
    """

    def validate(self, data: Any):
        code = _code(data)
        tree = _parse(code)

        run_task_fn = None
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_task":
                run_task_fn = node
                break
        if run_task_fn is None:
            raise ValueError(
                "async def run_task(task, ctx, reporter=None) 가 필요합니다. "
                "동기 def run_task 또는 누락은 허용되지 않습니다."
            )

        has_update = "update_task" in code
        has_save = "ctx.save()" in code or ".save()" in code
        if not has_update:
            raise ValueError("ctx.update_task(...) 호출이 최소 1회 필요합니다.")
        if not has_save:
            raise ValueError("ctx.save() 호출이 필요합니다.")

        return data

class JsonLiteralInPythonValidator(BaseValidator):
    """JSON true/false/null 을 Python identifier 로 쓰면 exec NameError — codegen 에서 거부.

    visual/narrative 가 echarts_spec 등 JSON 예시를 그대로 복사할 때 발생.
    재시도 루프 대신 validator 로 플랫폼이 막는다.
    """

    _JSON_NAMES = frozenset({"true", "false", "null"})

    def validate(self, data: Any):
        code = _code(data)
        tree = _parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in self._JSON_NAMES:
                py = {"true": "True", "false": "False", "null": "None"}[node.id]
                raise ValueError(
                    f"JSON 리터럴 {node.id!r} 금지 — Python dict 에는 {py} 사용 "
                    "(echarts_spec JSON 예시를 코드에 그대로 붙여넣지 말 것)"
                )
        return data


class TaskExecutorPatternsValidator(BaseValidator):
    """런타임 anti-pattern — ``sage.report.codegen_contract`` 와 동기.

    위반 시 같은 generate 에서 LLM 재생성 (llm_retry=True).
    사용자에게 다시 요청시키지 않는다.
    """

    def validate(self, data: Any):
        code = _code(data)
        for pattern, msg in FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                raise ValueError(msg)

        for m in PROGRESS_MSG_RE.finditer(code):
            msg = m.group(1)
            if PROGRESS_JARGON_RE.search(msg):
                raise ValueError(
                    f"progress 메시지에 내부 용어 금지 ({msg[:48]}…) — "
                    "사용자 친화 한글만 ([데이터][조회][분석] 등, reporter_progress.md)"
                )
        return data

class McpCallValidator(BaseValidator):
    """await call(tool_path, name, args) — tools spec name·input.properties 만 허용.

    왜 존재하는가
    -------------
    LLM 이 tools_spec 에 없는 name 을 '그럴듯하게' 지어 call 하면, MCP 서버가
    런타임에 unknown tool 로 실패한다. 또한 input.properties 밖 키·required 누락도
    FastMCP/도구 측에서 늦게 터진다. codegen 단계에서 스펙과 불일치를 거부한다.

    데이터 흐름
    -----------
    configure(또는 configure_mcp_validator) → build_mcp_call_specs →
    ``allowed_calls`` / ``call_specs`` 주입 → ``_iter_calls`` 로 AST 상수 call 추출 →
    (path,name) 소속 · properties 여분 · required 누락 검사.

    edge cases
    ----------
    - call() 이 코드에 없으면 통과(도구 미사용 태스크).
    - call 은 있으나 allowed_calls 비어 있으면 실패: '스펙 없이 추측 호출' 차단.
    - args 가 동적 dict 면 arg_keys=None → 키 검사 skip, name 매칭만 수행.
    """

    def __init__(self) -> None:
        super().__init__()
        self.allowed_calls: set[tuple[str, str]] = set()
        self.call_specs: dict[tuple[str, str], dict[str, Any]] = {}

    def validate(self, data: Any):
        calls = _iter_calls(_code(data))
        if not calls:
            return data

        if not self.allowed_calls:
            names = ", ".join(f"{n}@{p}" for p, n, _, _ in calls)
            raise ValueError(
                f"MCP call() 이 있으나 등록된 tools spec 이 없습니다: {names}. "
                "spec 에 없는 name 추측 호출 금지."
            )

        bad: list[str] = []
        for path, name, arg_keys, line in calls:
            key = (path, name)
            if key not in self.allowed_calls:
                allowed = sorted(f"{n}@{p}" for p, n in self.allowed_calls)
                bad.append(
                    f"L{line}: call({path!r}, {name!r}) — "
                    f"허용: {', '.join(allowed) or '(없음)'}"
                )
                continue
            if arg_keys is None:
                continue
            inp = self.call_specs.get(key) or {}
            props = set((inp.get("properties") or {}).keys())
            required = set(inp.get("required") or [])
            extra = arg_keys - props
            if extra:
                bad.append(
                    f"L{line}: call({path!r}, {name!r}) args {sorted(extra)!r} — "
                    f"spec input.properties 에 없음. 허용: {sorted(props) or '(없음)'}"
                )
            missing = required - arg_keys
            if missing:
                bad.append(
                    f"L{line}: call({path!r}, {name!r}) required 누락: {sorted(missing)!r}"
                )
        if bad:
            raise ValueError("MCP call() spec 불일치:\n" + "\n".join(bad))
        return data

class SchemaContractValidator(BaseValidator):
    """data — schema.py 필드 타입 contract (오류 유형별 패치 없음).

    ``validate_codegen_schema_contract`` 에 위임. schema_fields 는 configure 시
    load_pangea_schema_fields 로 채워지며, 비어 있으면 contract 모듈이 no-op
    또는 완화된 경로를 탄다. 오류 메시지를 유형별로 '고쳐 주는' 패치는 하지
    않고 거부만 한다 — LLM 재생성에 맡긴다.
    """

    schema_fields: dict[str, dict[str, str]] = {}

    def validate(self, data: Any):
        validate_codegen_schema_contract(_code(data), self.schema_fields)
        return data


class DataTaskFlowValidator(BaseValidator):
    """data 태스크 Pangea 갱신 파이프라인.

    **계약 정합**: LLM body 는 import 금지(LlmImportForbiddenValidator).
    ``call`` 등은 ``task_prelude.py`` 주입 — 여기서 import 문자열을 요구하면 안 됨.
    ``_scripts/test_codegen_contract.py`` 로 모순 재발을 CI/로컬에서 검사.

    계약하는 최소 흐름
    ------------------
    PangeaExDataFrame(did) → to_pandas(model) → (옵션 MCP) plan_updates →
    call → queue_update → apply_pending_updates(model) → ctx.update_task(...).

    ``requires_mcp`` 가 True 일 때만 MCP 분기·apply_pending_updates·하드코딩/가짜데이터 검사.
    False(파일 소스 only)면 Pangea 로드 + update_task 만 — tools 없이 parquet 로드 가능.

    TaskContext key 이름은 plan task ``instruction``·``description`` 에 따름 — validator 가
    특정 key 이름을 강제하지 않는다.

    기타 edge:
    - plan_updates item["keys"] 는 list — dict.get 접근 금지(키 혼동 사고).
    - queue_update + datetime.date() 금지 — JSON 직렬화/스키마는 'YYYY-MM-DD' 문자열.
    - allowed_models 이 주입되면 model 리터럴을 metadata 와 대조.
    """

    _BASE_SNIPPETS = (
        ("PangeaExDataFrame", "PangeaExDataFrame(did=task.data_id) — proto:pangea_api"),
        ("to_pandas", "to_pandas(model)"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.requires_mcp: bool = False
        self.allowed_models: set[str] | None = None

    def validate(self, data: Any):
        code = _code(data)
        missing = [hint for token, hint in self._BASE_SNIPPETS if token not in code]
        if missing:
            raise ValueError("data 태스크 필수 흐름 누락:\n- " + "\n- ".join(missing))
        if code.count("update_task") < 1:
            raise ValueError(
                "data: ctx.update_task 로 TaskContext 등록 필요 — "
                "key·description 은 plan task instruction 따름"
            )

        if self.allowed_models:
            bad_models = _detect_invalid_model_literals(code, self.allowed_models)
            if bad_models:
                raise ValueError(
                    "data 태스크: model 이름은 dataset_context [PANGEA TARGETS] 만:\n- "
                    + "\n- ".join(bad_models)
                )

        if self.requires_mcp:
            if "apply_pending_updates" not in code:
                raise ValueError(
                    "data 태스크(MCP): apply_pending_updates(model) 필수 — "
                    "model 인자 포함 (proto:pangea_api)"
                )
            if "plan_updates" not in code:
                raise ValueError(
                    "data 태스크: MCP call 전 plan_updates(model, keys=...) 필수 — "
                    "dump TTL 만료분만 call, plan 빈 list 이면 MCP 생략 (proto:pangea_api)"
                )
            if not re.search(r"plan_updates\s*\((?:.|\n){0,400}?keys\s*=", code):
                raise ValueError(
                    "data 태스크: plan_updates(model, keys=선정목록) — keys 생략 금지 "
                    "(0행 parquet 에서 빈 plan → MCP 생략). proto:pangea_api"
                )
            if "call(" not in code:
                raise ValueError(
                    "data 태스크: MCP tools 할당 — await call(path, name, args) 필수 "
                    "(prelude 주입 — body 에 import 금지). "
                    "plan_updates → call → queue_update 순서 ([[report/data_anti_hardcode]])"
                )
            if "queue_update" in code and "call(" not in code:
                raise ValueError("queue_update without call() — 하드코딩 payload 금지")
            if '["keys"].get' in code or "['keys'].get" in code or '["keys"]["' in code:
                raise ValueError(
                    'plan_updates item["keys"] 는 list — .get()·dict 접근 금지. '
                    'for key in item["keys"]: 사용 (proto:pangea_api)'
                )

            hardcoded = _detect_hardcoded_data_records(code)
            fake_patterns = _detect_fake_data_patterns(code)
            if hardcoded or fake_patterns:
                detail = hardcoded + fake_patterns
                raise ValueError(
                    "data 태스크: 하드코딩·가짜 데이터 금지 (tools spec call 결과만 사용):\n- "
                    + "\n- ".join(detail)
                )

        if "queue_update" in code and re.search(r"datetime\.date\s*\(", code):
            raise ValueError(
                "queue_update payload 의 date 는 datetime.date() 대신 "
                "'YYYY-MM-DD' 문자열 또는 API 반환값 그대로 사용"
            )
        return data

class AnalyzeTaskValidator(BaseValidator):
    """analyze — upstream 로드·집계 산출.

    데이터는 칠판(get_result) 또는 Pangea 원본(to_pandas) 중 하나에서 와야 한다.
    df.index.name 조건 reset_index / executor 내 BaseModel 정의는 과거 실패
    패턴(인덱스 가정·스키마 클래스 남발)이라 금지. 접근 anti-pattern 은
    ``_check_ctx_data_access`` / ``_check_pangea_to_pandas`` 공유.
    """

    def validate(self, data: Any):
        code = _code(data)
        if "ctx.get_result(" not in code and "PangeaExDataFrame" not in code:
            raise ValueError(
                "analyze: 중간 산출물 ctx.get_result(task_id, key) 또는 "
                "통합 PangeaExDataFrame(did=task.data_id).to_pandas(model) 필수"
            )
        _check_ctx_data_access(code)
        _check_pangea_to_pandas(code)
        if re.search(r"if\s+df\.index\.name\s", code):
            raise ValueError(
                "df.index.name 조건으로 reset_index() 하지 말 것 — upstream json 은 dict/list, Pangea 는 to_pandas"
            )
        if re.search(r"class\s+\w+\s*\(\s*BaseModel\s*\)", code):
            raise ValueError(
                "analyze: executor 내 Pydantic BaseModel 정의 금지 — dict/list/json 산출"
            )
        hardcoded = _detect_hardcoded_data_records(code)
        if hardcoded:
            raise ValueError(
                "analyze: 집계 수치 dict/list 리터럴 하드코딩 금지 — "
                "upstream/Pangea 집계만 사용:\n- " + "\n- ".join(hardcoded)
            )
        return data

class VisualTaskValidator(BaseValidator):
    """visual — chart/table TaskContext 등록.

    프론트는 echart Option dict / table {header,dtypes,data} 만 소비한다.
    pyecharts 래퍼·read_parquet 직접 파일 I/O 는 레이아웃 계약·스토리지 계약을
    깨뜨리므로 차단. 최소 1회 update_task 로 산출을 칠판에 남겨야
    narrative/release 의 attach_catalog_visuals 가 발견할 수 있다.
    """

    def validate(self, data: Any):
        code = _code(data)
        if code.count("update_task") < 1:
            raise ValueError("visual: ctx.update_task 로 chart/table 산출 등록 필요")
        if "ctx.get_result(" not in code and "PangeaExDataFrame" not in code:
            raise ValueError(
                "visual: 중간 산출물 ctx.get_result(task_id, key) 또는 "
                "통합 PangeaExDataFrame(did=task.data_id).to_pandas(model) 필수"
            )
        _check_ctx_data_access(code)
        _check_pangea_to_pandas(code)
        if re.search(r"\b(pyecharts|from\s+echarts\b)", code):
            raise ValueError("pyecharts/echarts 래퍼 금지 — echart Option dict 만 사용")
        if re.search(r"""['"]grid['"]\s*:\s*\[""", code) or re.search(r"\bgridIndex\b", code):
            raise ValueError(
                "visual: grid 배열·gridIndex 서브플롯 금지 — "
                "단일 grid object. 비교는 시리즈 겹치기 또는 차트 2개 "
                "(프론트가 grid 배열을 접어 차트가 안 보임)"
            )
        if re.search(r"read_parquet\s*\(", code):
            raise ValueError(
                "visual: pd.read_parquet 금지 — PangeaExDataFrame.to_pandas 또는 ctx.get_result"
            )
        hardcoded = _detect_hardcoded_data_records(code)
        if hardcoded:
            raise ValueError(
                "visual: 차트/표 수치 dict 리터럴 하드코딩 금지 — "
                "upstream 집계만 사용:\n- " + "\n- ".join(hardcoded)
            )
        return data

class NarrativeTaskValidator(BaseValidator):
    """narrative — ReportDocument 초안 (release 와 동일 규격).

    구 스키마(sections / data_refs) 와 새 스키마(layout_blocks + data)가 공존하던
    이행기 잔재를 거른다. build_report_document 의 키워드도 ``layout=`` 가 아니라
    ``layout_blocks=`` 여야 한다(API 시그니처와 일치).
    'name' 컬럼·task- 리터럴은 upstream json_keys / task.context 를 무시하는
    환각이므로 금지.
    """

    def validate(self, data: Any):
        code = _code(data)
        written = _update_task_keys(code)
        if NARRATIVE_DRAFT_KEY not in written:
            raise ValueError(
                f'narrative: ctx.update_task(..., key="{NARRATIVE_DRAFT_KEY}", ...) 또는 '
                f'{NARRATIVE_DRAFT_KEY}=draft 필요 (runner → draft.json, context_keys)'
            )
        if "build_report_document" not in code:
            raise ValueError("narrative: build_report_document(...) 필수 — sections/data_refs 구 스키마 금지")
        if re.search(r'"sections"\s*:', code) or "data_refs" in code:
            raise ValueError("narrative: sections/data_refs 구 스키마 금지 — layout+data ReportDocument 사용")
        if re.search(r"""=\s*['"]task-""", code):
            raise ValueError("narrative: upstream task_id 하드코딩 금지 — task.context[i] 사용")
        _check_ctx_data_access(code)
        _check_pangea_to_pandas(code)
        if re.search(r"build_report_document\s*\([^)]*\blayout\s*=", code):
            if "layout_blocks" not in code:
                raise ValueError(
                    "narrative: build_report_document layout= 만 있음 — "
                    "layout_blocks= 또는 layout=([blocks]) 사용"
                )
        if "build_report_document" in code and "layout_blocks" not in code and "layout=" not in code:
            raise ValueError("narrative: build_report_document(..., layout_blocks=...) 필수")
        if re.search(
            r"""['"]header['"]\s*:\s*\[\s*(['"][A-Za-z][A-Za-z0-9_]*['"]\s*,\s*)+['"][A-Za-z][A-Za-z0-9_]*['"]""",
            code,
        ):
            raise ValueError(
                "narrative: table header 는 한글 표시 라벨 — "
                "sector/foreign_total 등 영문 필드명을 header 에 쓰지 말 것 "
                "(data 키는 영문, header/columns.label 은 한글)"
            )
        if re.search(r"""['"]grid['"]\s*:\s*\[""", code) or re.search(r"\bgridIndex\b", code):
            raise ValueError(
                "narrative: 차트 grid 배열·gridIndex 금지 — 단일 grid "
                "(프론트가 배열을 접어 차트가 안 보임)"
            )
        hardcoded = _detect_hardcoded_data_records(code)
        if hardcoded:
            raise ValueError(
                "narrative: 표/차트 수치 dict 리터럴(데모 업종·가짜 순매수) 금지 — "
                "upstream get_result 만 사용. 비어 있으면 빈 표+데이터 없음 문구, 예시 수치 금지:\n- "
                + "\n- ".join(hardcoded)
            )
        return data

class ReleaseTaskValidator(BaseValidator):
    """release — LLM QA codegen (report_qa 함수 금지).

    upstream 소스는 apply_upstream_patches(rid, {tid: [ops]}) 로만 반영.
    draft/upstream embed 는 instruction·attach 가이드 — AST 길이/triple-quote gate 없음.
    """

    def validate(self, data: Any):
        code = _code(data)
        written = _update_task_keys(code)
        if not any(k in written for k in RELEASE_REPORT_KEYS):
            raise ValueError(
                f'release: ctx.update_task(..., key="{RELEASE_REPORT_KEY}", ...) 또는 '
                f'report=... 필요 (runner → report.json, legacy: {list(RELEASE_REPORT_KEYS)})'
            )
        if RELEASE_SUMMARY_KEY not in written:
            raise ValueError(
                f'release: ctx.update_task(..., key="{RELEASE_SUMMARY_KEY}", ...) 또는 '
                f'{RELEASE_SUMMARY_KEY}=... 필수 — QA 변경 overview·changes[]'
            )
        if "apply_upstream_source_updates" in code:
            from sage.report.release_contract import RELEASE_FORBIDDEN_PATTERNS

            raise ValueError(RELEASE_FORBIDDEN_PATTERNS[0][1])
        if "apply_upstream_patches" not in code:
            from sage.report.release_contract import MSG_PATCH_REQUIRED

            raise ValueError(MSG_PATCH_REQUIRED)
        if re.search(
            r"apply_upstream_patches\s*\(\s*[^,]+,\s*\{[^}]*task\.task_id",
            code,
        ):
            from sage.report.release_contract import MSG_SELF_PATCH_ONLY

            raise ValueError(MSG_SELF_PATCH_ONLY)
        if "finalize_report_document" not in code and "build_report_document" not in code:
            raise ValueError("release: finalize_report_document(...) 또는 build_report_document(...) 필수")
        if re.search(r"\breport_qa\b|review_report_data|sanitize_table_payload|is_junk_display", code):
            raise ValueError(
                "release: report_qa/review_report_data 등 자동 QA 함수 금지 — "
                "codegen 시 [REFERENCE DATA] 첨부본 검토 후 data patch 를 executor 에 작성"
            )
        if "fetch_upstream" in code:
            raise ValueError(
                "release: fetch_upstream 금지 — ctx.get_result(task_id, key) 사용"
            )
        if "narrative_to_layout" in code:
            raise ValueError(
                "release: sections/data_refs 구 스키마 재조립 금지 — report_document patch 만"
            )
        if "finalize_report_document" in code:
            if not all(k in code for k in ("plan_id=", "did=", "rid=")):
                raise ValueError(
                    "release: finalize_report_document(..., plan_id=task.plan_id, "
                    "did=task.data_id, rid=ctx.rid) 필수"
                )
        tofu_literal = (
            code.count("\u2006")
            + code.count("\u2004")
            + code.count("\u2005")
            + code.count("\u2009")
            + code.count("\u200a")
        )
        tofu_escape = len(re.findall(r"\\u200[0-9a-bA-B]", code, re.I))
        if tofu_literal >= 8 or tofu_escape >= 6:
            from sage.report.release_contract import MSG_HANGUL_TOFU

            raise ValueError(MSG_HANGUL_TOFU)
        return data

class PlanStructureValidator(BaseValidator):
    """Plan DAG·tools 할당 일관성.

    executor 코드가 아니라 ``ReportPlanOutput`` 을 검증한다(다른 validator 와
    입력 타입이 다름). runner 가 topo 실행·tools resolve 하기 전에 plan 자체의
    구조적 모순을 끊는다.

    검사 항목
    ---------
    1. task_id 유일 · context 참조가 tasks 집합에 존재
    2. ``topo_sort_tasks`` 로 사이클/정렬 불가 DAG 거부
    3. context=[] root 중 type==data 최소 1개 — 데이터 없는 analyze 만 있는 plan 방지
    4. task.tools ⊆ plan.tools (plan.tools 가 비어 있으면 skip — 상속/기본값 경로)
    5. release.context ⊇ 모든 narrative·visual + narrative 의 context
       (release 가 QA 때 선행 산출을 모두 볼 수 있어야 함)

    data 태스크 tools 비어 있어도 통과 — 파일 소스만 있는 데이터셋은 MCP 없이
    Pangea parquet 로드만으로 구성 가능(아래 인라인 주석과 동일 정책).
    """

    def validate(self, data: Any):
        if not isinstance(data, ReportPlanOutput):
            return data

        plan: ReportPlanOutput = data
        ids = [t.task_id for t in plan.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("plan.tasks 에 중복 task_id 가 있습니다.")

        by_id = {t.task_id: t for t in plan.tasks}
        for task in plan.tasks:
            for dep in task.context:
                if dep not in by_id:
                    raise ValueError(f"plan.tasks: context {dep!r} 가 tasks 에 없습니다.")

        try:
            topo_sort_tasks(plan.tasks)
        except ValueError as exc:
            raise ValueError(f"plan DAG 오류: {exc}") from exc

        roots = [t for t in plan.tasks if not t.context]
        if not any(t.type == "data" for t in roots):
            raise ValueError("context: [] 인 root data 태스크가 최소 1개 필요합니다.")

        plan_tools = set(plan.tools or [])
        for task in plan.tasks:
            for path in task.tools or []:
                if plan_tools and path not in plan_tools:
                    raise ValueError(
                        f"{task.task_id}: tools {path!r} 가 plan.tools 에 없습니다."
                    )
            # data 태스크: 파일 소스만 있는 데이터셋은 MCP tool 없이 Pangea parquet 로드만으로 구성 가능

        visual_ids = {t.task_id for t in plan.tasks if t.type == "visual"}
        narrative_ids = {t.task_id for t in plan.tasks if t.type == "narrative"}
        for task in plan.tasks:
            if task.type != "release":
                continue
            required = set(narrative_ids) | visual_ids
            for nt in plan.tasks:
                if nt.type == "narrative":
                    required.update(nt.context)
            missing = required - set(task.context)
            if missing:
                raise ValueError(
                    f"release 태스크 {task.task_id}: context 에 narrative·visual 및 "
                    f"narrative 선행 태스크가 필요합니다. 누락: {sorted(missing)}"
                )

        return data


# 모든 task_type 에 붙는 공통 suite — 빠른 실패 순(문법→import→구조→패턴→MCP→칠판).
_COMMON_VALIDATORS: list[type[BaseValidator]] = [
    TaskCodeSyntaxValidator,
    LlmImportForbiddenValidator,
    JsonLiteralInPythonValidator,
    RunTaskStructureValidator,
    TaskExecutorPatternsValidator,
    McpCallValidator,
    UpstreamBoardValidator,
]

# 타입별 추가 suite. PlanStructureValidator 는 plan Node 경로에서 별도 등록.
_TYPE_VALIDATORS: dict[str, list[type[BaseValidator]]] = {
    "data": [SchemaContractValidator, DataTaskFlowValidator],
    "analyze": [AnalyzeTaskValidator],
    "visual": [VisualTaskValidator],
    "narrative": [NarrativeTaskValidator],
    "release": [ReleaseTaskValidator],
}

def task_validators_for(task_type: str) -> list[BaseValidator]:
    """공통 + 타입별 validator 인스턴스 목록 — configure 전에 호출."""
    validators: list[BaseValidator] = [cls() for cls in _COMMON_VALIDATORS]
    for cls in _TYPE_VALIDATORS.get(task_type, []):
        validators.append(cls())
    return validators


def run_task_code_validators(code: str, *, task_type: str | None = None) -> None:
    """저장 직전 최소 검증 (import·구조·anti-pattern) — board/MCP 없이.

    ``validate_codegen_output`` 과의 차이:
    - McpCallValidator / UpstreamBoardValidator / SchemaContract 등 *주입 필수*
      validator 를 돌리지 않는다 (허용집합 없이 돌리면 오거부).
    - configure_task_validators / await 불필요 → 동기 저장 경로에서 호출 가능.
    - task_type 이 주어지면 타입별 validator 도 돌리되, 그 안의 requires_mcp·
      schema_fields·board 는 기본값(비활성/빈)이므로 MCP/칠판 규칙은 사실상 skip.

    wrap 객체는 BaseValidator 가 ``data.code`` 를 기대하므로 최소 attribute 만 흉내.
    """
    wrap = type("_TaskCodeWrap", (), {"code": code})()
    for cls in (
        TaskCodeSyntaxValidator,
        AssembledSourceValidator,
        RunTaskStructureValidator,
        TaskExecutorPatternsValidator,
    ):
        cls().validate(wrap)
    if task_type:
        for cls in _TYPE_VALIDATORS.get(task_type, []):
            cls().validate(wrap)


async def validate_codegen_output(
    code: str,
    *,
    task_type: str,
    plan_id: str,
    data_id: str,
    rid: str | None = None,
    context: list[str] | None = None,
    tools: list[str] | None = None,
) -> None:
    """NodeV 이후 2차 검증 — configure 된 전체 validator suite.

    호출측(프레임워크 NodeV 후처리)이 plan_id/data_id/context/tools 를 잡으면
    여기서 suite 조립 → 주입 → 순차 validate. 실패 시 ValueError 가 재시도
    루프의 교정 신호로 쓰인다.

    run_task_code_validators 보다 무겁고 정확하다: MCP allow-list·칠판 key·
    schema contract 까지 포함한다.
    """
    validators = task_validators_for(task_type)
    kwargs = {
        "type": task_type,
        "plan_id": plan_id,
        "data_id": data_id,
        "rid": rid,
        "context": list(context or []),
        "tools": list(tools or []),
    }
    await configure_task_validators(validators, kwargs)
    wrap = type("_TaskCodeWrap", (), {"code": code})()
    from sage.errs import CodegenContractError

    for validator in validators:
        try:
            validator.validate(wrap)
        except Exception as exc:
            if not getattr(validator, "llm_retry", True):
                raise CodegenContractError(str(exc), category=validator.name) from exc
            raise
