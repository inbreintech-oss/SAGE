from sage.models.node import TaskCodegenInput, TaskOutput
from sage.report.task_codegen import TaskCodegenNode
from sage.nodes import node

@node(input=TaskCodegenInput, output=TaskOutput)
class ReleaseTask(TaskCodegenNode):
    __task_type__ = "release"
