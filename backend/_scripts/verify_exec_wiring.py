"""Exec wiring static check — report / pangea / tool -> sage.exec.runtime (docker_pool only)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROUTES = [
    (
        "POST /report/generate",
        "report_task",
        "iter_plan_tasks -> run_task -> run_task_code",
        "sage/report/runner.py",
        ("run_task_code", "build_report_task_job", "run_exec_job"),
    ),
    (
        "POST /report/exec",
        "report_task",
        "iter_report_exec -> run_task -> run_task_code",
        "sage/report/runner.py",
        ("run_task_code", "build_report_task_job", "run_exec_job"),
    ),
    (
        "POST /data/pangeaze",
        "pangea_unify",
        "_run_unify_data -> run_exec_job",
        "routers/data.py",
        ("_run_unify_data", "build_pangea_unify_job", "run_exec_job"),
    ),
    (
        "POST /tool/exec",
        "tool_caller",
        "execute_caller_with_fix -> run_tool_caller",
        "sage/tool/runtime.py",
        ("run_tool_caller", "_run_caller_via_exec"),
    ),
    (
        "tool smoke (execute_with_fix)",
        "tool_caller",
        "execute -> run_tool_caller -> run_exec_job",
        "sage/exec/runtime.py",
        ("run_tool_caller", "run_exec_job"),
    ),
    (
        "POST /tool/generate smoke",
        "tool_caller",
        "handle_tool_generation -> execute_with_fix + TaskReporter",
        "routers/tool.py",
        ("TaskReporter", "iter_while", "execute_with_fix"),
    ),
]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    import cfg

    print(f"SAGE_EXEC_DRIVER={cfg.sage_exec_driver}")
    print()

    ok = True
    for label, kind, path, rel, needles in ROUTES:
        text = _read(rel)
        wired = all(n in text for n in needles)
        status = "OK" if wired else "FAIL"
        if not wired:
            ok = False
        print(f"[{status}] {label} ({kind})")
        print(f"       {path}")
        print(f"       file: {rel}")
        print()

    rt = _read("sage/exec/runtime.py")
    if "run_docker_pool" in rt and "inprocess" not in rt:
        print("[OK] sage/exec/runtime.py docker_pool-only")
    else:
        print("[FAIL] sage/exec/runtime.py must be docker_pool-only")
        ok = False

    wc = _read("sage/exec/worker_core.py")
    if "exec_import_shims" in wc:
        print("[OK] sage/exec/worker_core.py import shims")
    else:
        print("[FAIL] sage/exec/worker_core.py import shims")
        ok = False

    df = _read("docker/sage-exec/Dockerfile")
    if "COPY sage/" not in df and "PYTHONPATH=/host/n2" in df:
        print("[OK] docker/sage-exec/Dockerfile mount-only (no sage bake)")
    else:
        print("[FAIL] docker/sage-exec/Dockerfile must not COPY sage/")
        ok = False

    dc = _read("docker-compose.exec.yml")
    if 'PYTHONPATH: /host/n2' in dc and "/opt/sage-exec" not in dc:
        print("[OK] docker-compose.exec.yml PYTHONPATH=/host/n2 only")
    else:
        print("[FAIL] docker-compose.exec.yml PYTHONPATH")
        ok = False

    if hasattr(cfg, "sage_exec_allow_inprocess_fallback"):
        print("[FAIL] cfg.sage_exec_allow_inprocess_fallback must be removed")
        ok = False
    else:
        print("[OK] no inprocess fallback config")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
