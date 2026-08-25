"""실행 traceback → codegen 재시도용 수정 힌트 (contract 기반 범용)."""

from __future__ import annotations

import re


def execution_fix_hints(traceback_text: str) -> str:
    """traceback → 준수해야 할 contract 안내 (오류 유형별 패치 없음)."""
    if not traceback_text:
        return ""
    hints: list[str] = []
    tb = traceback_text

    if "schema contract" in tb.lower() or "SchemaContractError" in tb:
        hints.append(
            "schema contract: queue_update record 필드 타입은 dataset_context schema.py 와 "
            "일치해야 함 — 변환 함수 없이 API 값을 타입에 맞게 직접 매핑"
        )

    if re.search(r"Validator|contract 위반|필수 import|spec 불일치", tb, re.I):
        hints.append(
            "validator 오류 메시지·instruction.md·runtime_contract 를 그대로 준수해 "
            "전체 run_task 를 수정"
        )

    if "ModuleNotFoundError" in tb or "ImportError" in tb:
        hints.append("import: runtime_contract example/run_task.py 와 동일한 경로만 사용")

    if re.search(r"TypeError.*await|can't be awaited", tb, re.I):
        hints.append("safe_report / ctx.save / reporter.update — await 금지 (동기 호출)")

    if not hints:
        return ""
    return "\n".join(f"- {h}" for h in hints[:4])
