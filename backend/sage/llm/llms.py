"""LLM clients, factory, and shared request helpers for NodeV and routers."""

import hashlib
import json
import os
import re
import tempfile
import time
import asyncio
import concurrent.futures
import contextvars
import threading
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Dict, List, Type, TypeVar, Union, Optional, Any

from anthropic import Anthropic
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv

from sage.errs import (
    ServiceUnavailableError,
    QuotaExceededError,
    LLMTimeoutError,
    is_quota_error,
)
from sage.llm.usage import record_llm_usage
from sage.logg import warning, error
from sage.llm.gemini_schema import build_gemini_response_model, normalize_gemini_json_response
from utils.cache import cache
from utils.conv import sanitize_tree

load_dotenv(find_dotenv())

client = None
gemini_client = None
MAX_RETRIES = 3

# LLM generate() 전체(attach 업로드 + API) timeout — env SAGE_LLM_TIMEOUT_SEC
LLM_REQUEST_TIMEOUT_SEC = float(os.environ.get("SAGE_LLM_TIMEOUT_SEC", "120"))
# Cursor Agent는 로컬 bridge 기동·대용량 codegen attach 때문에 기본 한도를 더 길게 둠
CURSOR_LLM_TIMEOUT_SEC = float(
    os.environ.get(
        "SAGE_CURSOR_TIMEOUT_SEC",
        os.environ.get("SAGE_LLM_TIMEOUT_SEC", "600"),
    )
)
LLM_EXECUTOR_WORKERS = int(os.environ.get("SAGE_LLM_EXECUTOR_WORKERS", "8"))

_LLM_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_LLM_EXECUTOR_GUARD = threading.Lock()

# --- TaskContext / llm_attach 크기 제한 — sage.report.context_limits ---
from sage.report.context_limits import (
    CONTEXT_JSON_MAX_BYTES,
    CONTEXT_JSON_MAX_DICT_KEYS,
    CONTEXT_JSON_MAX_LIST_ITEMS,
    json_payload_byte_size,
    validate_context_json_shape,
    validate_context_json_value,
)

LLM_ATTACH_MAX_BYTES = int(os.environ.get("SAGE_LLM_ATTACH_MAX_BYTES", "262144"))
LLM_ATTACH_RELEASE_MAX_BYTES = int(os.environ.get("SAGE_LLM_ATTACH_RELEASE_MAX_BYTES", "524288"))

_T = TypeVar("_T")


def validate_llm_attach(attach: dict[str, Any], *, task_type: str | None = None) -> None:
    """codegen generate() 직전 llm_attach 패킷 크기 검증."""
    from sage.errs import ContextAttachTooLargeError

    if not attach:
        return
    size = json_payload_byte_size(attach)
    limit = LLM_ATTACH_RELEASE_MAX_BYTES if task_type == "release" else LLM_ATTACH_MAX_BYTES
    if size > limit:
        raise ContextAttachTooLargeError(size, limit)


def _llm_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _LLM_EXECUTOR
    if _LLM_EXECUTOR is None:
        with _LLM_EXECUTOR_GUARD:
            if _LLM_EXECUTOR is None:
                _LLM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                    max_workers=max(1, LLM_EXECUTOR_WORKERS),
                    thread_name_prefix="sage-llm",
                )
    return _LLM_EXECUTOR


def shutdown_llm_executor(*, wait: bool = False) -> None:
    """프로세스 종료 시 LLM thread pool 정리."""
    global _LLM_EXECUTOR
    with _LLM_EXECUTOR_GUARD:
        if _LLM_EXECUTOR is None:
            return
        try:
            _LLM_EXECUTOR.shutdown(wait=wait, cancel_futures=True)
        except Exception:
            pass
        _LLM_EXECUTOR = None


def _call_with_timeout(fn: Callable[[], _T], *, timeout_sec: float | None = None) -> _T:
    """Sync helper — shared LLM executor + timeout (legacy sync callers)."""
    limit = LLM_REQUEST_TIMEOUT_SEC if timeout_sec is None else timeout_sec
    fut = _llm_executor().submit(fn)
    try:
        return fut.result(timeout=limit)
    except concurrent.futures.TimeoutError as exc:
        raise LLMTimeoutError(limit) from exc

_ATTACH_MIME = {
    ".json": "application/json",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

def _env_api_key(name: str) -> str | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    return raw.strip().strip("'").strip('"')


def _ensure_cursor_sdk_compat() -> None:
    """cursor-sdk uses os.get_blocking (Python 3.12+)."""
    if not hasattr(os, "get_blocking"):
        os.get_blocking = lambda fd: True  # type: ignore[attr-defined]
        os.set_blocking = lambda fd, blocking: None  # type: ignore[attr-defined]


def _extract_json_text(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return stripped
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _structured_json_instruction(response_model: Type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        "\n\n### 출력 (JSON only)\n"
        "응답은 **단일 JSON 객체**만 반환하세요. markdown 코드펜스·설명 문장 금지.\n"
        f"모델: `{response_model.__name__}`\n"
        f"```json\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n```"
    )


def _mime_for_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _ATTACH_MIME.get(ext, "application/octet-stream")

class Message(BaseModel):
    """Single chat turn passed to :meth:`LLMInterface.generate`."""

    role: str = Field(description="메시지를 보낸 주체 (역할)")
    content: str = Field(description="메시지의 내용")

class LLMInterface(ABC):
    """Abstract LLM backend — sync ``generate`` and async ``generate_async``."""

    @abstractmethod
    def generate(
            self,
            messages: List[Message] | str,
            attach: Optional[Union[dict, list, str]] = None,
            response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        """Call the model and return text (or JSON when ``response_model`` is set)."""
        pass

    async def generate_async(
            self,
            messages: List[Message] | str,
            attach: Optional[Union[dict, list, str]] = None,
            response_model: Optional[Type[BaseModel]] = None,
            **kwargs: Any,
    ) -> str:
        """Run :meth:`generate` in a thread pool without blocking the event loop."""
        loop = asyncio.get_running_loop()
        limit = LLM_REQUEST_TIMEOUT_SEC
        ctx = contextvars.copy_context()

        def _run() -> str:
            return ctx.run(
                self.generate,
                messages,
                attach=attach,
                response_model=response_model,
                **kwargs,
            )

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_llm_executor(), _run),
                timeout=limit,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(limit) from exc

# --- 구체적인 LLM 구현체들 ---

class GPT5LLM(LLMInterface):
    """새로운 기본값으로 설정될 LLM 구현체."""
    model_name = 'gpt-5'  # 'gpt-4.1'
    api_key = os.environ.get('GPT_API_KEY')
    endpoint = 'https://ib-aoai-test.openai.azure.com/openai/v1/'

    def generate(
            self,
            messages: Union[List[Message], str],
            attach: Optional[Union[dict, list, str]] = None,
            response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        global client
        if not client:
            client = OpenAI(base_url=self.endpoint, api_key=self.api_key)

        # 1. 메시지 구조화 (System / User 분리)
        formatted_messages = []

        # 입력된 messages가 리스트일 경우와 문자열일 경우 처리
        if isinstance(messages, str):
            formatted_messages.append({"role": "user", "content": messages})
        else:
            for m in messages:
                formatted_messages.append({"role": m.role, "content": m.content})

        # 2. 대용량 첨부 데이터(attach) 처리
        # OpenAI는 파일 핸들을 넘기는 기능이 없으므로, 데이터가 크더라도
        # 메시지 컨텍스트 최상단에 별도의 '데이터 블록'으로 배치합니다.
        if attach:
            attach_str = ""
            if isinstance(attach, (dict, list)):
                # [지침 반영] ensure_ascii=False 적용
                attach_str = json.dumps(attach, ensure_ascii=False, indent=2)
            elif isinstance(attach, str) and os.path.exists(attach):
                with open(attach, "r", encoding='utf-8') as f:
                    attach_str = f.read()
            elif isinstance(attach, str):
                attach_str = attach

            if attach_str:
                # 데이터가 길 경우, 모델이 헷갈리지 않게 시스템 지시문 바로 뒤에
                # [REFERENCE DATA] 섹션으로 최우선 배치합니다.
                data_message = {
                    "role": "system",
                    "content": f"이하 제공되는 데이터를 바탕으로 분석을 수행하십시오.\n\n[REFERENCE DATA START]\n{attach_str}\n[REFERENCE DATA END]"
                }
                # 시스템 메시지 위치(보통 인덱스 0)에 삽입
                formatted_messages.insert(0, data_message)

        # 3. API 호출
        def _api_call() -> str:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                timeout=LLM_REQUEST_TIMEOUT_SEC,
            )
            content = completion.choices[0].message.content
            usage = getattr(completion, "usage", None)
            if usage is not None:
                record_llm_usage(
                    self.model_name,
                    getattr(usage, "prompt_tokens", 0) or 0,
                    getattr(usage, "completion_tokens", 0) or 0,
                    provider="gpt",
                )
            return content if content else "Error: Empty response."

        try:
            return _api_call()
        except LLMTimeoutError:
            raise
        except Exception as e:
            if is_quota_error(e):
                raise QuotaExceededError() from e
            return f"API Call Error: {str(e)}"

class GeminiLLM(LLMInterface):
    """Gemini 모델 LLM 구현체 — attach 는 File API 업로드 우선."""

    model_name = 'gemini-3.5-flash'  # 'gemini-2.5-flash'  # 'gemini-3.5-flash'  # 'gemini-3-flash-preview'  # 'gemini-3.1-pro-preview'  # 'gemini-2.5-flash'  # 또는 'gemini-3.1-pro'
    api_key = os.environ.get('GEMINI_API_KEY')

    def _get_client(self):
        global gemini_client
        if not gemini_client:
            timeout_ms = int(LLM_REQUEST_TIMEOUT_SEC * 1000)
            gemini_client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
        return gemini_client

    def _wait_upload_ready(self, client, uploaded_file, *, timeout_sec: int = 60) -> None:
        name = uploaded_file.name
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            state = uploaded_file.state
            state_name = state.name if hasattr(state, "name") else str(state)
            if state_name == "ACTIVE":
                return
            if state_name == "FAILED":
                raise RuntimeError(f"Gemini file upload failed: {name}")
            time.sleep(1)
            uploaded_file = client.files.get(name=name)
        raise TimeoutError(f"Gemini file not ready: {name}")

    def _upload_file_part(self, client, file_path: str) -> types.Part:
        mime_type = _mime_for_path(file_path)
        uploaded_file = client.files.upload(
            file=file_path,
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        self._wait_upload_ready(client, uploaded_file)
        return types.Part(
            file_data=types.FileData(
                file_uri=uploaded_file.uri,
                mime_type=uploaded_file.mime_type or mime_type,
            )
        )

    def _attach_as_text_part(self, attach: Union[dict, list, str]) -> types.Part:
        if isinstance(attach, (dict, list)):
            attach = sanitize_tree(attach)
            text = json.dumps(attach, ensure_ascii=False, indent=2)
            label = "[참조 데이터(JSON)]"
        elif isinstance(attach, str) and os.path.exists(attach):
            with open(attach, "r", encoding="utf-8") as f:
                text = f.read()
            label = f"[파일 내용({attach})]"
        else:
            text = str(attach)
            label = "[참조 데이터]"
        return types.Part(text=f"\n{label}:\n{text}")

    def _build_attach_parts(self, client, attach: Union[dict, list, str]) -> List[types.Part]:
        tmp_file_path = None
        try:
            if isinstance(attach, (dict, list)):
                attach = sanitize_tree(attach)
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as tmp:
                    json.dump(attach, tmp, ensure_ascii=False, indent=2)
                    tmp_file_path = tmp.name
                return [self._upload_file_part(client, tmp_file_path)]

            if isinstance(attach, str) and os.path.isfile(attach):
                return [self._upload_file_part(client, attach)]

            return [self._attach_as_text_part(attach)]
        except Exception as exc:
            warning(f"Gemini file upload fallback to text inject: {exc}")
            return [self._attach_as_text_part(attach)]
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

    def generate(
            self,
            messages: Union[List[Message], str],
            attach: Optional[Union[dict, list, str]] = None,
            response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        return self._generate_inner(messages, attach, response_model=response_model)

    def _generate_inner(
            self,
            messages: Union[List[Message], str],
            attach: Optional[Union[dict, list, str]] = None,
            *,
            response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        from sage.llm.llms import validate_llm_attach

        if isinstance(attach, dict):
            validate_llm_attach(attach)
        client = self._get_client()

        payload_parts: List[types.Part] = []
        sys_inst = "당신은 데이터 분석 전문가입니다."

        if isinstance(messages, str):
            payload_parts.append(types.Part(text=messages))
        else:
            for msg in messages:
                if msg.role == 'system':
                    sys_inst = msg.content
                else:
                    payload_parts.append(types.Part(text=f"{msg.role}: {msg.content}"))

        if attach:
            payload_parts.extend(self._build_attach_parts(client, attach))

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                config_kwargs: dict[str, Any] = {
                    "temperature": 0 if response_model else 0.7,
                    "system_instruction": sys_inst,
                    "max_output_tokens": 32768 if response_model else 8192,
                }
                if response_model is not None:
                    gemini_schema, _ = build_gemini_response_model(response_model)
                    config_kwargs["response_mime_type"] = "application/json"
                    config_kwargs["response_schema"] = gemini_schema

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=[types.Content(role="user", parts=payload_parts)],
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                um = getattr(response, "usage_metadata", None)
                if um is not None:
                    record_llm_usage(
                        self.model_name,
                        getattr(um, "prompt_token_count", 0) or 0,
                        getattr(um, "candidates_token_count", 0) or 0,
                        provider="gemini",
                    )
                raw = response.text or ""
                if response_model is not None:
                    return normalize_gemini_json_response(raw, response_model)
                return raw

            except ClientError as e:
                if is_quota_error(e):
                    raise QuotaExceededError() from e
                raise e
            except ServerError as e:
                status = getattr(e, 'status_code', None)
                if status == 503 or "503" in str(e) or "UNAVAILABLE" in str(e):
                    retry_count += 1
                    if retry_count >= max_retries:
                        error(f"Gemini 서버 과부하(503)가 지속, {retry_count}/{max_retries}회 재시도 모두 실패")
                        raise ServiceUnavailableError

                    warning(f"Gemini 서버 과부하(503). {retry_count}/{max_retries}회 재시도 중...")
                    time.sleep(3)
                    continue
                raise e

class ClaudeLLM(LLMInterface):
    """Claude 4.6 Sonnet 모델 및 Beta File API(Link 방식) 구현체."""

    # 요청하신 모델 ID 적용
    model_name = 'claude-sonnet-4-6'
    api_key = os.environ.get('CLAUDE_API_KEY')

    def generate(
            self,
            messages: Union[List[Message], str],
            attach: Optional[Union[dict, list, str]] = None,
            response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        global client
        if not client:
            client = Anthropic(api_key=self.api_key)

        # 1. 메시지 정규화
        system_prompt = "당신은 MCP(Model Context Protocol) 도구 개발 전문가입니다."
        user_messages = []

        if isinstance(messages, str):
            user_messages.append({"role": "user", "content": messages})
        else:
            for m in messages:
                if m.role == 'system':
                    system_prompt = m.content
                else:
                    role = "assistant" if m.role == "assistant" else "user"
                    user_messages.append({"role": role, "content": m.content})

        try:
            # 2. 첨부 데이터(attach)를 텍스트로 변환 (base64/document 사용 안 함)
            attach_text = ""
            if attach:
                if isinstance(attach, (dict, list)):
                    attach_text = json.dumps(attach, ensure_ascii=False, indent=2)
                elif isinstance(attach, str) and os.path.exists(attach):
                    with open(attach, "r", encoding="utf-8") as f:
                        attach_text = f.read()
                else:
                    attach_text = str(attach)

            # 3. 메시지 본문 구성 (순수 텍스트 블록 방식)
            final_messages = []
            for i, msg in enumerate(user_messages):
                if i == len(user_messages) - 1 and msg["role"] == "user" and attach_text:
                    # XML 태그로 데이터를 감싸서 모델이 구분하기 쉽게 만듭니다.
                    combined_text = f"<attached_data>\n{attach_text}\n</attached_data>\n\n{msg['content']}"
                    final_messages.append({"role": "user", "content": combined_text})
                else:
                    final_messages.append(msg)

            # 4. API 호출
            def _api_call() -> str:
                response = client.messages.create(
                    model=self.model_name,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=final_messages,
                    timeout=LLM_REQUEST_TIMEOUT_SEC,
                )
                usage = getattr(response, "usage", None)
                if usage is not None:
                    record_llm_usage(
                        self.model_name,
                        getattr(usage, "input_tokens", 0) or 0,
                        getattr(usage, "output_tokens", 0) or 0,
                        provider="claude",
                    )
                return response.content[0].text

            return _api_call()

        except LLMTimeoutError:
            raise
        except Exception as e:
            if is_quota_error(e):
                raise QuotaExceededError() from e
            raise RuntimeError(f"Claude API Call Error: {str(e)}") from e


class CursorLLM(LLMInterface):
    """Cursor Agent LLM — GeminiLLM 과 동일한 Message/attach/response_model 계약."""

    model_name = os.environ.get("SAGE_CURSOR_MODEL", "composer-2.5")
    runtime = os.environ.get("SAGE_CURSOR_RUNTIME", "local").lower()
    _api_base = "https://api.cursor.com/v1"

    @property
    def api_key(self) -> str | None:
        return _env_api_key("CURSOR_API_KEY")

    def _attach_as_text(self, attach: Union[dict, list, str]) -> str:
        if isinstance(attach, (dict, list)):
            attach = sanitize_tree(attach)
            text = json.dumps(attach, ensure_ascii=False, indent=2)
            label = "[참조 데이터(JSON)]"
        elif isinstance(attach, str) and os.path.exists(attach):
            with open(attach, "r", encoding="utf-8") as f:
                text = f.read()
            label = f"[파일 내용({attach})]"
        else:
            text = str(attach)
            label = "[참조 데이터]"
        return f"\n{label}:\n{text}"

    def _build_prompt(
        self,
        messages: Union[List[Message], str],
        attach: Optional[Union[dict, list, str]],
        response_model: Optional[Type[BaseModel]],
    ) -> tuple[str, str]:
        sys_inst = "당신은 데이터 분석 전문가입니다."
        parts: List[str] = []

        if isinstance(messages, str):
            parts.append(messages)
        else:
            for msg in messages:
                if msg.role == "system":
                    sys_inst = msg.content
                else:
                    parts.append(f"{msg.role}: {msg.content}")

        if attach:
            parts.append(self._attach_as_text(attach))

        if response_model is not None:
            sys_inst = (sys_inst + _structured_json_instruction(response_model)).strip()

        return sys_inst, "\n\n".join(parts)

    def _finalize_response(
        self,
        raw: str,
        response_model: Optional[Type[BaseModel]],
    ) -> str:
        if response_model is None:
            return raw or ""
        json_text = _extract_json_text(raw)
        response_model.model_validate_json(json_text)
        return normalize_gemini_json_response(json_text, response_model)

    def _cursor_request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        timeout_sec: float | None = None,
    ) -> dict:
        key = self.api_key
        if not key:
            raise RuntimeError("CURSOR_API_KEY is not set")

        url = f"{self._api_base}{path}"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=payload, headers=headers, method=method)
        limit = LLM_REQUEST_TIMEOUT_SEC if timeout_sec is None else timeout_sec

        try:
            with urllib.request.urlopen(req, timeout=limit) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 or is_quota_error(Exception(detail)):
                raise QuotaExceededError() from exc
            raise RuntimeError(f"Cursor API {exc.code}: {detail}") from exc

    def _generate_cloud(self, sys_inst: str, prompt: str) -> str:
        full_text = f"{sys_inst}\n\n{prompt}" if sys_inst else prompt
        created = self._cursor_request(
            "POST",
            "/agents",
            {
                "prompt": {"text": full_text},
                "model": {"id": self.model_name},
                "skipReviewerRequest": True,
            },
            timeout_sec=min(60.0, LLM_REQUEST_TIMEOUT_SEC),
        )
        agent_id = created["agent"]["id"]
        run_id = created["run"]["id"]
        deadline = time.time() + CURSOR_LLM_TIMEOUT_SEC
        terminal = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})
        result_text = ""

        try:
            while time.time() < deadline:
                run = self._cursor_request(
                    "GET",
                    f"/agents/{agent_id}/runs/{run_id}",
                    timeout_sec=min(30.0, LLM_REQUEST_TIMEOUT_SEC),
                )
                status = str(run.get("status", "")).upper()
                if status in terminal:
                    if status != "FINISHED":
                        raise RuntimeError(
                            f"Cursor run {status}: {run.get('result', '')}"
                        )
                    result_text = run.get("result") or ""
                    from sage.llm.pricing import estimate_tokens_from_chars

                    record_llm_usage(
                        self.model_name,
                        estimate_tokens_from_chars(len(full_text)),
                        estimate_tokens_from_chars(len(result_text)),
                        provider="cursor",
                        estimated=True,
                    )
                    break
                time.sleep(2)
            else:
                raise LLMTimeoutError(LLM_REQUEST_TIMEOUT_SEC)
        finally:
            try:
                self._cursor_request("DELETE", f"/agents/{agent_id}", timeout_sec=30.0)
            except Exception as exc:
                warning(f"Cursor agent cleanup failed ({agent_id}): {exc}")

        return result_text

    def _generate_local(self, sys_inst: str, prompt: str) -> str:
        from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions

        _ensure_cursor_sdk_compat()
        key = self.api_key
        if not key:
            raise RuntimeError("CURSOR_API_KEY is not set")

        cwd = os.environ.get("NARRATIX_HOME", os.getcwd())
        full_prompt = f"{sys_inst}\n\n{prompt}" if sys_inst else prompt

        try:
            result = Agent.prompt(
                full_prompt,
                AgentOptions(
                    api_key=key,
                    model=self.model_name,
                    local=LocalAgentOptions(cwd=cwd),
                ),
            )
        except CursorAgentError as exc:
            if is_quota_error(exc):
                raise QuotaExceededError() from exc
            raise RuntimeError(f"Cursor agent startup failed: {exc}") from exc

        status = str(getattr(result, "status", "")).lower()
        if status == "error":
            raise RuntimeError(f"Cursor run failed: {getattr(result, 'result', '')}")

        usage = getattr(result, "usage", None)
        if usage is not None:
            record_llm_usage(
                self.model_name,
                getattr(usage, "input_tokens", 0) or 0,
                getattr(usage, "output_tokens", 0) or 0,
                provider="cursor",
            )
        else:
            from sage.llm.pricing import estimate_tokens_from_chars

            record_llm_usage(
                self.model_name,
                estimate_tokens_from_chars(len(full_prompt)),
                estimate_tokens_from_chars(len(getattr(result, "result", "") or "")),
                provider="cursor",
                estimated=True,
            )
        return getattr(result, "result", None) or ""

    @property
    def request_timeout_sec(self) -> float:
        return CURSOR_LLM_TIMEOUT_SEC

    async def generate_async(
        self,
        messages: List[Message] | str,
        attach: Optional[Union[dict, list, str]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ) -> str:
        loop = asyncio.get_running_loop()
        limit = self.request_timeout_sec
        ctx = contextvars.copy_context()

        def _run() -> str:
            return ctx.run(
                self.generate,
                messages,
                attach=attach,
                response_model=response_model,
                **kwargs,
            )

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_llm_executor(), _run),
                timeout=limit,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(limit) from exc

    def generate(
        self,
        messages: Union[List[Message], str],
        attach: Optional[Union[dict, list, str]] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> str:
        if isinstance(attach, dict):
            validate_llm_attach(attach)

        sys_inst, prompt = self._build_prompt(messages, attach, response_model)

        try:
            if self.runtime == "cloud":
                raw = self._generate_cloud(sys_inst, prompt)
            else:
                raw = self._generate_local(sys_inst, prompt)
            return self._finalize_response(raw, response_model)
        except (LLMTimeoutError, QuotaExceededError):
            raise
        except Exception as exc:
            if is_quota_error(exc):
                raise QuotaExceededError() from exc
            raise RuntimeError(f"Cursor LLM Error: {exc}") from exc


class LLMFactory:
    """Resolve ``SAGE_LLM_TYPE`` to a concrete :class:`LLMInterface` implementation."""

    # 맵에 신규 LLM 추가
    _llm_map: Dict[str, Type[LLMInterface]] = {
        "gpt-5": GPT5LLM,  # 새로운 기본값
        "gemini": GeminiLLM,
        "claude": ClaudeLLM,
        "cursor": CursorLLM,
    }

    # 기본 LLM — env SAGE_LLM_TYPE (gemini|gpt-5|claude|cursor)
    DEFAULT_LLM_TYPE = os.environ.get("SAGE_LLM_TYPE", "gemini").lower()

    @staticmethod
    def get_llm(llm_type: str) -> LLMInterface:
        """Return an LLM instance for ``gemini``, ``gpt-5``, ``claude``, or ``cursor``."""
        llm_class = LLMFactory._llm_map.get(llm_type.lower())
        if not llm_class:
            raise ValueError(f"지원되지 않는 LLM 타입입니다: {llm_type}")
        return llm_class()

if __name__ == '__main__':
    print(GeminiLLM().generate('안녕, 내 이름을 영어로 작성해줘', attach={'name': '현철'}))
    # print(GeminiLLM().generate('안녕, 내 이름을 영어로 작성해줘'))
