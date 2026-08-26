import ast
from typing import Any, Tuple, Optional, List

from sage.models.node import UserQuery
from sage.models.tool import ToolPack
from sage.nodes import node, NodeV, BaseValidator

import sage.mcp as mcpc


class ToolAccessValidator(BaseValidator):
    """
    caller 소스 내 call() 함수 호출 시 허용된 tool_name만 사용하는지 검증
    """

    def __init__(self, allowed_tools: List[str]):
        super().__init__()
        # allowed_tools는 UserQuery에서 추출된 허용 도구 이름 리스트
        self.allowed_tools = allowed_tools

    def validate(self, data: Any):
        # ToolPack 객체에서 caller 소스 추출
        caller_source = getattr(data, "caller", "")
        if not caller_source:
            raise ValueError("검증할 caller 소스코드가 존재하지 않습니다.")

        # ast.parse에서 문법 오류 발생 시 자동으로 SyntaxError가 터지며 실패 처리됨
        tree = ast.parse(caller_source)

        # 소스 코드 내 모든 함수 호출 노드 순회
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 1. 호출 함수 이름이 'call'인지 확인
                if isinstance(node.func, ast.Name) and node.func.id == 'call':
                    # 2. 인자 개수 확인 (tool_name, func_name, args...)
                    if len(node.args) >= 1:
                        tool_arg = node.args[0]

                        # 3. 첫 번째 인자가 문자열 상수('tool_name')인 경우 검증
                        if isinstance(tool_arg, ast.Constant):
                            tool_name = tool_arg.value

                            # 허용된 도구 목록에 없는 경우 즉시 에러 발생
                            if tool_name not in self.allowed_tools:
                                raise PermissionError(
                                    f"허용되지 않은 도구 '{tool_name}' 호출이 감지되었습니다. "
                                    f"현재 사용 가능한 도구 목록은 {self.allowed_tools} 입니다. "
                                    f"await call() 첫 인자를 {self.allowed_tools} 중 하나로 바꿔라. "
                                    "generate 초안 tm-* tool_id 는 허용 목록에 없으면 호출 금지."
                                )

        return data


class CallerMcpImportValidator(BaseValidator):
    """caller 는 sage.mcp.call 을 import 한다. kwargs['call'] 함수 주입 금지."""

    def validate(self, data: Any):
        from sage.tool.caller_contract import assert_caller_mcp_import, caller_source_of

        assert_caller_mcp_import(caller_source_of(data))
        return data


@node(input=UserQuery, output=ToolPack)
class ToolExecutor(NodeV):
    """ 도구 실행 노드 """

    def __init__(self):
        super().__init__(
            validators=[
                ToolAccessValidator(allowed_tools=[]),
                CallerMcpImportValidator(),
            ]
        )

    async def run(self, **kwargs):
        # 허용된 도구 이름 리스트 실행 시간 주입
        allowed_names = kwargs.get('tools', [])
        for v in self.validators:
            if isinstance(v, ToolAccessValidator):
                v.allowed_tools = allowed_names

        return await super().run(**kwargs)
