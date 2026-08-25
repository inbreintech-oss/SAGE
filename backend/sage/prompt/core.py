import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

import cfg

BASE_DIR = Path(__file__).parent.parent
DOTPROMPTS_DIR_NAME = ".prompts"
INCLUDE_PATTERN = re.compile(r"\[\[(.+?)\]\]")
NAMESPACE_REF_PATTERN = re.compile(r"^([^:]+):(.+)$")

def dotprompts_dir() -> Path:
    return Path(cfg.nodes_path) / DOTPROMPTS_DIR_NAME

def find_model_prompt(model_name_snake: str) -> Optional[Path]:
    """NodeV output schema 가이드 — nodes/.prompts/{tool,report,data}/{name}.md"""
    base = dotprompts_dir()
    if not base.is_dir():
        return None
    for candidate in (
        base / "tool" / f"{model_name_snake}.md",
        base / "report" / f"{model_name_snake}.md",
        base / "data" / f"{model_name_snake}.md",
        base / f"{model_name_snake}.md",
    ):
        if candidate.is_file():
            return candidate
    matches = sorted(base.rglob(f"{model_name_snake}.md"))
    return matches[0] if matches else None

def _first_existing(paths: list[Path]) -> Optional[Path]:
    for path in paths:
        if path.is_file():
            return path
    return None

def _md_filename(name: str) -> str:
    return name if name.endswith(".md") else f"{name}.md"

def _resolve_dotprompts(ref: str) -> Optional[Path]:
    """
    [[report/runtime]] → nodes/.prompts/report/runtime.md
    [[tool/tool_pack_codegen]] → nodes/.prompts/tool/tool_pack_codegen.md
    [[tool_pack]] → nodes/.prompts/**/tool_pack.md (rglob)
    """
    base = dotprompts_dir()
    if not base.is_dir():
        return None

    if "/" in ref:
        namespace, subpath = ref.split("/", 1)
        if not namespace or not subpath:
            return None
        ns_base = base / namespace
        if not ns_base.is_dir():
            return None
        rel = Path(subpath.replace("/", os.sep))
        direct = ns_base / rel
        if direct.is_file():
            return direct
        stem = ns_base / rel
        if stem.suffix:
            return stem if stem.is_file() else None
        return _first_existing([
            Path(f"{stem}.md"),
            Path(f"{stem}.py"),
            Path(f"{stem}.json"),
        ])

    name = _md_filename(ref)
    return _first_existing(sorted(base.rglob(name)))

def _embed_example(path: Path) -> str:
    body = path.read_text(encoding="utf-8").strip()
    if path.suffix == ".json":
        return f"```json\n{body}\n```"
    if path.suffix == ".py":
        return f"```python\n{body}\n```"
    return body

def _resolve_include_ref(ref: str, current_dir: Path) -> Optional[Path]:
    ref = ref.strip()

    dotprompt = _resolve_dotprompts(ref)
    if dotprompt is not None:
        return dotprompt

    ns_match = NAMESPACE_REF_PATTERN.match(ref)
    if ns_match:
        namespace, name = ns_match.group(1), ns_match.group(2)
        if namespace == "node":
            local = Path(current_dir) / _md_filename(name)
            return local if local.is_file() else None
        return None

    filename = _md_filename(ref)
    local = Path(current_dir) / filename
    if local.is_file():
        return local

    return None

def resolve_pattern(text: str, current_dir: Path | None = None) -> str:
    """
    [[namespace/path]] 또는 [[name]] 패턴을 nodes/.prompts 파일 내용으로 치환한다.

    - [[report/runtime]] — nodes/.prompts/report/runtime.md
    - [[tool/tool_pack_codegen]] — nodes/.prompts/tool/tool_pack_codegen.md
    - [[node:name]] — instruction.md 와 같은 폴더의 name.md
    """
    current_dir = Path(current_dir or dotprompts_dir())

    def get_replacement_value(match: re.Match) -> str:
        original_text = match.group(0)
        ref = match.group(1).strip()
        filepath = _resolve_include_ref(ref, current_dir)
        if filepath is None:
            return original_text
        try:
            if filepath.suffix in (".py", ".json"):
                return _embed_example(filepath)
            return filepath.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"[경고] {ref} 로드 중 오류 ({filepath}): {e}")
            return ""

    current_text = text
    for _ in range(10):
        new_text, count = INCLUDE_PATTERN.subn(get_replacement_value, current_text)
        if count == 0:
            break
        current_text = new_text

    return current_text

def replace_args(prompt_dict: Dict[str, str], **kwargs) -> Dict[str, str]:
    """args 섹션의 header와 regex 치환 로직을 실행합니다."""
    if not prompt_dict:
        return {}

    if "args" not in prompt_dict:
        return prompt_dict

    for arg_name, arg_spec in prompt_dict["args"].items():
        if arg_name in kwargs:
            value = kwargs[arg_name]
        elif "default" in arg_spec:
            value = arg_spec["default"]
        else:
            continue

        if isinstance(value, dict):
            substitution_value = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            substitution_value = str(value)

        if "regex" in arg_spec:
            regex_format = arg_spec["regex"]
            try:
                pattern = re.compile(re.escape(regex_format).replace(r"\{\{\}\}", r"(.*?)"), re.DOTALL)
                replacement = regex_format.replace("{{}}", substitution_value)
                if pattern.search(prompt_dict["user"]):
                    prompt_dict.update({"user": pattern.sub(replacement, prompt_dict["user"], 1)})
            except re.error:
                continue
        elif "header" in arg_spec:
            header = arg_spec["header"]
            pattern = re.compile(rf"# {re.escape(header)}\s*(.*?)(?=#|\Z)", re.DOTALL)
            replacement = f"# {header}\n{substitution_value}\n"
            if pattern.search(prompt_dict["user"]):
                prompt_dict.update({"user": pattern.sub(replacement, prompt_dict["user"], 1)})

    return prompt_dict

def compose(path_or_text: str, schema: str, **kwargs) -> str:
    """
    Markdown 파일을 로드하여 동적 참조와 변수를 치환한 뒤
    최종 프롬프트(system/user)를 반환합니다.
    """
    candidates = [cfg.nodes_path / path_or_text / "instruction.md"]
    dot_path = _resolve_dotprompts(path_or_text)
    if dot_path is not None:
        candidates.insert(0, dot_path)

    target = next((p for p in candidates if p.is_file()), None)
    instructions = target.read_text(encoding="utf-8") if target else path_or_text

    inst_schema_enhanced = f"{instructions}\n\n{schema}".strip()
    current_dir = target.parent if target else dotprompts_dir()
    return resolve_pattern(inst_schema_enhanced, current_dir=current_dir)
