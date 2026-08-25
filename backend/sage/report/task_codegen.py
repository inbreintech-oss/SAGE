"""Report task codegen 노드 베이스 (모델은 sage.models.node)."""

from __future__ import annotations

from sage.nodes import NodeV, nodes
from sage.nodes.framework import BaseValidator


class TaskCodegenNode(NodeV):
    """Report task codegen 공통 베이스 — type 별 validator + MCP spec 주입."""

    __task_type__: str = ""

    def __init__(
        self,
        *,
        extra_validators: list[BaseValidator] | None = None,
        max_retries: int = 3,
    ):
        from sage.report.validators import task_validators_for

        validators = task_validators_for(self.__task_type__) + (extra_validators or [])
        super().__init__(validators=validators, max_retries=max_retries)

    async def run(self, **kwargs):
        from sage.report.validators import configure_task_validators

        await configure_task_validators(self.validators, kwargs)
        return await super().run(**kwargs)


TASK_NODE_PATH = {
    "data": "report/task/data",
    "analyze": "report/task/analyze",
    "visual": "report/task/visual",
    "narrative": "report/task/narrative",
    "release": "report/task/release",
}


def get_task_node(task_type: str):
    path = TASK_NODE_PATH.get(task_type)
    if not path:
        raise ValueError(f"unknown task type: {task_type!r}")
    return nodes[path]
