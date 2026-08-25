"""Pydantic output → Gemini 호환 structured output (모든 NodeV output 공통)."""

from __future__ import annotations

import inspect
import json
from typing import Any, Dict, List, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

_JSON_DESC_SUFFIX = " (JSON string — object/array 직렬화)"

# Gemini types.Schema 가 property 수준에서 허용하는 JSON Schema 키 (대략적 allowlist)
_GEMINI_PROPERTY_KEYS = frozenset({
    "type", "format", "description", "nullable", "enum", "items",
    "properties", "required", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "title", "default", "anyOf", "allOf", "oneOf",
    "$ref", "propertyOrdering", "minItems", "maxItems",
})


def _field_has_json_schema_extra(field_info: FieldInfo) -> bool:
    extra = field_info.json_schema_extra
    if extra is None:
        return False
    if callable(extra):
        return True
    return bool(extra)


def _constraints_from_field_info(field_info: FieldInfo) -> dict[str, Any]:
    """Pydantic Field metadata → Field() kwargs (min_length, pattern 등)."""
    out: dict[str, Any] = {}
    for item in field_info.metadata:
        name = type(item).__name__
        if name == "MinLen":
            out["min_length"] = item.min_length
        elif name == "MaxLen":
            out["max_length"] = item.max_length
        elif name == "Pattern":
            out["pattern"] = item.pattern
        elif name == "Ge":
            out["ge"] = item.ge
        elif name == "Le":
            out["le"] = item.le
        elif name == "Gt":
            out["gt"] = item.gt
        elif name == "Lt":
            out["lt"] = item.lt
    return out


def _gemini_field_from(field_info: FieldInfo) -> tuple[FieldInfo, bool]:
    """
    json_schema_extra 등 앱 전용 메타 제거 — Gemini response_schema 검증 통과용.
    description·기본 제약(min_length, pattern 등)은 유지.
    """
    if not _field_has_json_schema_extra(field_info):
        return field_info, False

    from pydantic_core import PydanticUndefined

    kwargs: dict[str, Any] = _constraints_from_field_info(field_info)
    if field_info.description is not None:
        kwargs["description"] = field_info.description
    if field_info.default is not PydanticUndefined:
        kwargs["default"] = field_info.default
        return Field(**kwargs), True
    if field_info.default_factory is not None:
        kwargs["default_factory"] = field_info.default_factory
        return Field(**kwargs), True
    return Field(**kwargs), True


def _schema_has_non_gemini_property_keys(node: Any) -> bool:
    """model_json_schema() 에 Gemini 가 거부하는 property 키가 있는지."""
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for prop in props.values():
                if isinstance(prop, dict):
                    unknown = set(prop.keys()) - _GEMINI_PROPERTY_KEYS
                    if unknown:
                        return True
        return any(_schema_has_non_gemini_property_keys(v) for v in node.values())
    if isinstance(node, list):
        return any(_schema_has_non_gemini_property_keys(v) for v in node)
    return False


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return args[0] if len(args) == 1 else annotation
    return annotation


def _is_basemodel_type(annotation: Any) -> bool:
    return inspect.isclass(annotation) and issubclass(annotation, BaseModel)


def _is_freeform_json_type(annotation: Any) -> bool:
    """Gemini 가 additionalProperties 로 거부하는 타입 — Dict·Any 등."""
    ann = _unwrap_optional(annotation)
    if ann is Any:
        return True
    origin = get_origin(ann)
    if origin is dict or ann is dict:
        return True
    if origin is Dict:
        return True
    return False


def _str_field_from(field_info: FieldInfo, *, suffix: str = _JSON_DESC_SUFFIX) -> FieldInfo:
    desc = (field_info.description or "").strip()
    if suffix not in desc:
        desc = f"{desc}{suffix}".strip()
    return Field(
        default=field_info.default,
        default_factory=field_info.default_factory,
        description=desc or None,
    )


def _schema_has_additional_properties(node: Any) -> bool:
    if isinstance(node, dict):
        if "additionalProperties" in node:
            return True
        return any(_schema_has_additional_properties(v) for v in node.values())
    if isinstance(node, list):
        return any(_schema_has_additional_properties(v) for v in node)
    return False


_GEMINI_CACHE: dict[Type[BaseModel], tuple[Type[BaseModel], tuple[tuple[str, ...], ...]]] = {}


def build_gemini_response_model(
    model: Type[BaseModel],
) -> tuple[Type[BaseModel], tuple[tuple[str, ...], ...]]:
    """
    NodeV output → Gemini response_schema 용 모델.
    Dict/Any 필드는 str(JSON) 로 치환하고 복원 경로를 반환.
    json_schema_extra 등 비표준 키는 Gemini Schema 에서 제거.
    변경 불필요 시 원본 모델 그대로 반환.
    """
    if model in _GEMINI_CACHE:
        return _GEMINI_CACHE[model]

    field_defs: dict[str, Any] = {}
    json_paths: list[tuple[str, ...]] = []
    changed = False

    for name, field_info in model.model_fields.items():
        ann = _unwrap_optional(field_info.annotation)
        gemini_field, stripped = _gemini_field_from(field_info)
        if stripped:
            changed = True
            field_info = gemini_field

        if _is_freeform_json_type(ann):
            changed = True
            json_paths.append((name,))
            field_defs[name] = (str, _str_field_from(field_info))
            continue

        list_origin = get_origin(ann)
        if list_origin is list or ann is list:
            args = get_args(ann)
            inner = _unwrap_optional(args[0]) if args else None
            if inner and _is_basemodel_type(inner):
                inner_model, inner_paths = build_gemini_response_model(inner)
                if inner_model is not inner:
                    changed = True
                    field_defs[name] = (list[inner_model], field_info)
                    for path in inner_paths:
                        json_paths.append((name, "__each__", *path))
                    continue
            field_defs[name] = (ann, field_info)
            continue

        if _is_basemodel_type(ann):
            nested_model, nested_paths = build_gemini_response_model(ann)
            if nested_model is not ann:
                changed = True
                field_defs[name] = (nested_model, field_info)
                for path in nested_paths:
                    json_paths.append((name, *path))
                continue
            field_defs[name] = (ann, field_info)
            continue

        field_defs[name] = (ann, field_info)

    needs_wrap = (
        changed
        or _schema_has_additional_properties(model.model_json_schema())
        or _schema_has_non_gemini_property_keys(model.model_json_schema())
    )
    if not needs_wrap:
        result = (model, ())
        _GEMINI_CACHE[model] = result
        return result

    for name, (ann, fi) in list(field_defs.items()):
        clean_fi, _ = _gemini_field_from(fi)
        field_defs[name] = (ann, clean_fi)

    gemini_model = create_model(
        f"{model.__name__}__Gemini",
        __base__=BaseModel,
        **field_defs,
    )

    paths = tuple(json_paths)
    result = (gemini_model, paths)
    _GEMINI_CACHE[model] = result
    return result


def _parse_json_at_path(node: Any, path: tuple[str, ...]) -> None:
    if not path:
        return
    head, *rest = path
    if head == "__each__":
        if isinstance(node, list):
            for item in node:
                _parse_json_at_path(item, tuple(rest))
        return
    if not isinstance(node, dict) or head not in node:
        return
    if not rest:
        val = node[head]
        if isinstance(val, str):
            try:
                node[head] = json.loads(val)
            except json.JSONDecodeError:
                pass
        return
    _parse_json_at_path(node[head], tuple(rest))


def normalize_gemini_json_response(
    text: str,
    response_model: Type[BaseModel],
) -> str:
    """Gemini JSON 응답 → 원본 Pydantic output 이 파싱 가능한 JSON."""
    _, json_paths = build_gemini_response_model(response_model)
    if not json_paths:
        return text
    data = json.loads(text)
    for path in json_paths:
        _parse_json_at_path(data, path)
    return json.dumps(data, ensure_ascii=False)
