"""TaskContext JSON size limits — LLM 모듈과 분리 (exec worker 경량 import)."""

from __future__ import annotations

import json
import os
from typing import Any

from utils.conv import sanitize_tree

CONTEXT_JSON_MAX_BYTES = int(os.environ.get("SAGE_CONTEXT_JSON_MAX_BYTES", "32768"))
CONTEXT_JSON_MAX_LIST_ITEMS = int(os.environ.get("SAGE_CONTEXT_JSON_MAX_LIST_ITEMS", "50"))
CONTEXT_JSON_MAX_DICT_KEYS = int(os.environ.get("SAGE_CONTEXT_JSON_MAX_DICT_KEYS", "32"))


def json_payload_byte_size(value: Any) -> int:
    return len(
        json.dumps(sanitize_tree(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def validate_context_json_shape(value: Any, *, key_hint: str = "") -> None:
    from sage.errs import ContextStorageError

    if not isinstance(value, (dict, list)):
        raise ContextStorageError(
            f"TaskContext value{(' ' + key_hint) if key_hint else ''} 는 dict 또는 list(JSON)만 허용됩니다."
        )
    hint = f" ({key_hint})" if key_hint else ""
    if isinstance(value, list) and len(value) > CONTEXT_JSON_MAX_LIST_ITEMS:
        raise ContextStorageError(
            f"list 원소 수 초과{hint}: {len(value)} > {CONTEXT_JSON_MAX_LIST_ITEMS}"
        )
    if isinstance(value, dict) and len(value) > CONTEXT_JSON_MAX_DICT_KEYS:
        raise ContextStorageError(
            f"dict key 수 초과{hint}: {len(value)} > {CONTEXT_JSON_MAX_DICT_KEYS}"
        )
    if isinstance(value, list):
        for i, item in enumerate(value):
            if isinstance(item, (dict, list)):
                validate_context_json_shape(
                    item, key_hint=f"{key_hint}[{i}]" if key_hint else f"[{i}]"
                )


def validate_context_json_value(value: Any, *, key_hint: str = "") -> None:
    from sage.errs import ContextPayloadTooLargeError

    validate_context_json_shape(value, key_hint=key_hint)
    size = json_payload_byte_size(value)
    if size > CONTEXT_JSON_MAX_BYTES:
        raise ContextPayloadTooLargeError(size, CONTEXT_JSON_MAX_BYTES, key_hint=key_hint)
