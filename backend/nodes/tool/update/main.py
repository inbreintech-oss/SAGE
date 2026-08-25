"""도구 수정 노드 — 기존 ToolPack 을 질의·SecretKey 안내에 맞게 패치한다."""

from sage.models.tool import ToolUpdateInput, ToolPack
from sage.nodes import node, NodeV
from sage.secret.prompt import build_secret_prompt
from sage.tool.generate_guide import build_tool_codegen_guide


@node(input=ToolUpdateInput, output=ToolPack)
class ToolUpdator(NodeV):
    async def run(self, **kwargs) -> ToolPack:
        secret_id = kwargs.get("secret_id")
        keys = kwargs.get("keys")
        user_id = kwargs.get("user_id") or "admin"
        base_query = kwargs.get("query") or ""
        parts = [base_query]
        guide = build_tool_codegen_guide(base_query)
        if guide:
            parts.append(guide)
        extra = await build_secret_prompt(secret_id, keys, user_id=user_id)
        if extra:
            parts.append(extra)
        kwargs = {**kwargs, "query": "\n\n".join(p for p in parts if p).strip()}
        return await super().run(**kwargs)
