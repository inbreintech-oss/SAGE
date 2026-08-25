"""TaskRun — run_task 첫 인자. codegen 입력 task 필드와 1:1 (runner 주입).

**import 작성 금지** — TaskRun, TaskContext, safe_report, call, PangeaExDataFrame,
pd, np 등은 runtime prelude 가 자동 주입.

async def run_task(task, ctx, reporter=None):
    safe_report(reporter, "[분석] PER/PBR 통계 계산 (28종목)", state="running")
    ...
    # 단일: ctx.update_task(task.task_id, key="...", value={...}, description="...")
    # 복수: ctx.update_task(task.task_id, chart_key=opt, table_key=tbl, description="...")
    ctx.save()

# 진행 보고 — [[report/reporter_progress]]
#   — 사용자 화면용 한글만. TaskContext/upstream/model명 금지
"""
