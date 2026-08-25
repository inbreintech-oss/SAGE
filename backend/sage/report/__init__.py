"""Report pipeline — plan DAG, task codegen, layout, task context."""

from .context import (
    CONTEXT_FILENAME,
    TaskContext,
    TaskInfo,
    TaskResult,
    infer_data_type,
    plan_id_to_hex,
)

_RUNNER_EXPORTS = {
    "RunTaskReporter",
    "TaskReporter",
    "TaskSourceError",
    "apply_upstream_source_updates",
    "collect_report_result",
    "codegen_task",
    "ensure_report_dirs",
    "downstream_task_closure",
    "iter_plan_tasks",
    "iter_report_exec",
    "load_plan_from_report",
    "make_run_dir",
    "missing_task_sources",
    "report_dir",
    "run_task",
    "safe_report",
    "save_plan",
    "save_run_meta",
    "task_context_for_report",
    "topo_sort_tasks",
}


def __getattr__(name: str):
    if name == "layout":
        from . import layout as _layout

        return _layout
    if name in _RUNNER_EXPORTS:
        from . import runner as _runner

        return getattr(_runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CONTEXT_FILENAME",
    "TaskContext",
    "TaskInfo",
    "TaskResult",
    "TaskReporter",
    "RunTaskReporter",
    "TaskSourceError",
    "apply_upstream_source_updates",
    "collect_report_result",
    "codegen_task",
    "ensure_report_dirs",
    "infer_data_type",
    "iter_plan_tasks",
    "iter_report_exec",
    "layout",
    "load_plan_from_report",
    "make_run_dir",
    "missing_task_sources",
    "plan_id_to_hex",
    "report_dir",
    "run_task",
    "safe_report",
    "save_plan",
    "save_run_meta",
    "task_context_for_report",
    "topo_sort_tasks",
    "downstream_task_closure",
]
