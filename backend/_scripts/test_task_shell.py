from sage.report.task_shell import assemble_task_source, assert_assembled, extract_task_body

body = """async def run_task(task, ctx, reporter=None):
    safe_report(reporter, "ok")
    ctx.update_task(task.task_id, key="x", value={"a": 1}, description="d")
    ctx.save()
"""
assembled = assemble_task_source(body)
assert_assembled(assembled)
assert "import pandas" not in extract_task_body(body)
print("task_shell ok")
