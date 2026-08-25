from sage.models.node import TaskUpdate
from sage.models.tool import ToolPack
from sage.nodes import node, NodeV
from sage import prompt as pp
import sage.mcp as mcpc

@node(input=TaskUpdate, output=ToolPack)
class TaskUpdator(NodeV):

    async def run(self, **kwargs):
        input = self.__node_input_model__(**kwargs)
        input.task.data = await pp.load_schema(input.task.data)
        input.task.tools = await mcpc.load_tools_spec(input.task.tools)
        return await super().run(**input.model_dump())
