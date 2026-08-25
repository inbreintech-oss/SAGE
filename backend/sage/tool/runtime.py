"""Tool runtime — dump generated sources, execute caller.py, and self-heal on failure."""

import json
import re
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

import numpy as np
import pandas as pd

from sage import nodes
from sage.config import TOOLS_DIR
from sage.logg import warning, debug, error

from sage.models.doc import ToolStatus
from sage.models.node import SourceFixed
from sage.models.tool import ToolPack
from sage.tool.metadata import write_metadata


async def _run_caller_via_exec(
    workspace: Path,
    kwargs: dict | None = None,
    *,
    reporter=None,
) -> Any:
    """``caller.py:main`` — sage.exec.runtime.run_tool_caller (docker_pool)."""
    from sage.exec.runtime import run_tool_caller

    result = await run_tool_caller(workspace, kwargs=kwargs, reporter=reporter)
    if not result.ok:
        raise RuntimeError(result.error or "tool caller exec failed")

    return_value = result.return_value
    if isinstance(return_value, dict) and "result" in return_value:
        return return_value["result"]
    return return_value


def generate_tool_id(tool_name):
    return f"tm-{tool_name.replace('_', '-')}-{str(uuid.uuid4())[:8]}"


def dump(tool_data: ToolPack, status: ToolStatus = "generated",
         target='all', instructions='', rid='', base_dir=TOOLS_DIR,
         secret_id: str | None = None):
    """ToolPack 을 tools/ 디렉터리에 저장 — main.py(coder) + caller.py(NL 실행기)."""

    # report 하위 경로에 넣을 때: rid/tool_id (리포트별 격리)
    tool_id_or_path = rid + '/' + tool_data.tool_id if rid else tool_data.tool_id

    tool_full_path = base_dir / tool_id_or_path  # tool_data.tool_id
    tool_full_path.mkdir(parents=True, exist_ok=True)

    # 3. 파일 및 메타데이터 저장
    if tool_data.code and target in ['all', 'code']:
        (tool_full_path / "main.py").write_text(tool_data.code, encoding='utf-8')

    if tool_data.caller:
        final_caller = finalize_caller_source(tool_data.caller)
        (tool_full_path / "caller.py").write_text(final_caller, encoding='utf-8')

    extra = {}
    if secret_id:
        extra["secret_id"] = secret_id
    dump_metadata(base_dir, tool_id_or_path, status, instructions, extra=extra)


def dump_metadata(base_dir, tool_id, status: ToolStatus, instructions='', extra=None):
    """tools/{id}/metadata.json 기록. extra 에 secret_id 를 넣으면 dump 덮어써도 유지된다."""
    write_metadata(tool_id, status=status, instructions=instructions, extra=extra)


def resolve_id(tool_name: str) -> str:
    """
    도구 이름을 입력받아 tools 내의 실제 tm-id를 찾아 반환합니다.
    패턴에 맞는 폴더가 여러 개일 경우 가장 최근 생성된 것을 반환합니다.
    """
    search_paths = [TOOLS_DIR]
    candidates = []

    # 정규식: tm-{이름}-{8자리UUID}
    # tool_name의 언더바(_)는 폴더 생성 시 하이픈(-)으로 치환되므로 이를 고려
    normalized_name = tool_name.replace('_', '-')
    pattern = re.compile(rf"^tm-{re.escape(normalized_name)}-[a-f0-9]{{8}}$")

    for path in search_paths:
        if not path.exists(): continue
        for entry in path.iterdir():
            if entry.is_dir() and pattern.match(entry.name):
                # 생성 시간(ctime)과 폴더명을 함께 저장
                candidates.append((entry.stat().st_ctime, entry.name))

    # 가장 최근 생성된 순으로 정렬 후 첫 번째 반환
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # 찾지 못하면 입력받은 이름 그대로 반환 (내장 도구 등)
    return tool_name


def finalize_caller_source(source: str) -> str:
    """
    caller 소스 내 get_transport_path 호출부의 도구 이름을 실제 tm-id로 교체합니다.
    """
    # 패턴: get_transport_path('도구이름' ... )
    pattern = r"get_transport_path\s*\(\s*['\"]([^'\"]+)['\"]"

    def _replacer(match):
        original_name = match.group(1)
        # 이미 치환된 ID면 스킵
        if original_name.startswith("tm-"):
            return match.group(0)

        resolved = resolve_id(original_name)
        return match.group(0).replace(original_name, resolved)

    return re.sub(pattern, _replacer, source)


async def execute(tool_id: str, *, reporter=None, **kwargs):
    """Dynamically load ``tools/{tool_id}/caller.py`` and await ``main(**kwargs)``.

    Args:
        tool_id: Folder name under ``TOOLS_DIR`` (e.g. ``tm-calc-a1b2c3d4``).
        **kwargs: Forwarded to the caller's ``main`` function.

    Returns:
        JSON-serializable result from ``main``.

    Raises:
        FileNotFoundError: Missing tool folder or ``caller.py``.
        RuntimeError: Missing ``main``, execution error, or non-serializable output.
    """
    target_folder = Path(TOOLS_DIR) / tool_id
    if not target_folder.is_dir():
        err_msg = f"도구 폴더를 찾을 수 없습니다. (ID: {tool_id})"
        error(err_msg)
        raise FileNotFoundError(err_msg)

    debug(f"Executing tool: {tool_id}")
    return await _run_caller_via_exec(target_folder, kwargs=kwargs, reporter=reporter)


def update_metadata(tool_id: str, status: str, result: Any = None):
    base_dir = TOOLS_DIR / tool_id
    meta_path = base_dir / "metadata.json"

    summary_result = None

    if result is not None:
        # 1. 결과가 Pandas DataFrame인 경우 별도 저장
        if isinstance(result, pd.DataFrame):
            result.to_parquet(base_dir / "result.parquet")
            summary_result = {
                "type": "dataframe",
                "shape": result.shape,
                "columns": list(result.columns),
                "file": "result.parquet"
            }
        # 2. 결과가 너무 큰 리스트나 딕셔너리인 경우 (예: 10KB 이상)
        elif len(str(result)) > 10240:
            with open(base_dir / "result_full.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
            summary_result = {
                "type": "large_json",
                "size_bytes": len(str(result)),
                "file": "result_full.json"
            }
        else:
            summary_result = result

    # 메타데이터 업데이트
    with open(meta_path, "r+", encoding="utf-8") as f:
        meta = json.load(f)
        meta["status"] = status
        meta["updated_at"] = datetime.now()
        meta["result_summary"] = summary_result

        f.seek(0)
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.truncate()


def _raise_if_tool_reported_fail(res: Any) -> None:
    """도구가 예외 대신 status=FAIL dict 를 반환하면 smoke 가 성공으로 오인한다."""
    payload = res
    if isinstance(payload, dict) and "result" in payload and isinstance(payload["result"], dict):
        payload = payload["result"]
    if not isinstance(payload, dict):
        return
    status = payload.get("status") or payload.get("Status")
    if isinstance(status, str) and status.strip().upper() in {"FAIL", "FAILED", "ERROR"}:
        msg = payload.get("message") or payload.get("msg") or payload.get("msg1") or payload
        raise RuntimeError(f"도구가 실패 상태를 반환했습니다: {msg}")


async def execute_with_fix(tool, max_retries=3, fix='all', *, reporter=None):
    """
    도구를 물리적으로 파일화(dump)하고 실행함.
    실패 시 ToolFix 노드를 통해 코드를 교정하며 재시도함.
    """
    retry_count = 0
    # tool_status: ToolStatus = "syntax-passed"

    while retry_count <= max_retries:
        try:
            # 도구 실행 시도
            res = await execute(tool.tool_id, reporter=reporter)
            _raise_if_tool_reported_fail(res)
            return res, tool
        except Exception as e:
            err_msg = traceback.format_exc()
            retry_count += 1

            if retry_count <= max_retries:
                warning(f"[{tool.title}] 실행 실패 ({retry_count}차). 코드 수정 진입. \n오류: {traceback.format_exc()}")

                # [Self-Correction] 에러 로그를 기반으로 도구 코드 교정
                fixer = nodes.ToolFix()
                tool = await fixer.run(tool=tool, error=err_msg, fix=fix)
                dump(tool, target=fix)
                continue
            else:
                # 모든 재시도 횟수 소과 시 최종 예외 발생
                raise RuntimeError(f"도구 실행 최종 실패 ({max_retries}회 시도 초과)")


async def execute_caller_with_fix(
        caller_code: str,
        max_retries: int = 3,
        *,
        reporter=None,
) -> Tuple[Any, str]:
    """
    caller 소스를 temp workspace 에 기록 후 exec 로 실행.
    오류 시 ErrorFix 노드로 소스를 수정하여 재시도함.
    """
    import cfg

    current_code = caller_code
    retry_count = 0
    workspace = Path(cfg.tools_path) / ".exec-caller" / uuid.uuid4().hex[:12]
    workspace.mkdir(parents=True, exist_ok=True)

    while retry_count <= max_retries:
        try:
            current_code = finalize_caller_source(current_code)
            (workspace / "caller.py").write_text(current_code, encoding="utf-8")
            result = await _run_caller_via_exec(workspace, reporter=reporter)
            try:
                json.dumps(result, ensure_ascii=False)
            except Exception as se:
                raise RuntimeError(f"데이터 직렬화 실패: {str(se)}")
            return result, current_code

        except Exception as e:
            err_msg = traceback.format_exc()
            retry_count += 1

            if retry_count <= max_retries:
                print(f"실행 오류 ({retry_count}/{max_retries}). ErrorFix 노드 호출...")

                fixer = nodes.SourceFix()
                res: SourceFixed = await fixer.run(code=current_code, error=err_msg)
                current_code = res.fixed_code
                continue

            raise RuntimeError(
                f"최종 실행 실패 ({max_retries}회 시도 초과).\n"
                f"최종 에러: {str(e)}"
            )
