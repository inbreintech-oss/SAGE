import asyncio
import re
import json
from typing import Optional, Type

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List, Dict, Any, Tuple
import ast

from sage.logg import info, warning  # warning 로그 추가
from sage.nodes import node, NodeV, BaseValidator
from sage.models.node import UserQuery
from sage.models.tool import ToolPack
import sage.mcp as mcpc
import sage.tool as tools

class ConcreteResultValidator(BaseValidator):
    """
    1. @mcp.tool() 데코레이터가 붙은 함수를 정확히 식별
    2. 비동기(async def) 및 일반(def) 함수 모두 지원
    3. 입력/출력 타입에 Dict, Any 등 모호한 타입 대신 구체적 Pydantic 모델 강제
    """

    def _check_concrete_type(self, node, func_name: str):
        """타입 힌트가 구체적인 모델인지 검사. 아니면 즉시 에러 발생"""
        is_concrete = False

        # 1. 단순 이름 (예: StockInfo)
        if isinstance(node, ast.Name):
            forbidden = ('Dict', 'Any', 'List', 'Optional', 'Union', 'dict', 'list', 'float', 'int', 'str')
            if node.id not in forbidden:
                is_concrete = True

        # 2. 속성 접근 (예: models.StockInfo)
        elif isinstance(node, ast.Attribute):
            is_concrete = True

        # 검증 실패 시 raise (Dict[str, Any]와 같은 Subscript도 여기서 걸림)
        if not is_concrete:
            raise ValueError(
                f"도구 '{func_name}'의 반환 타입이 구체적이지 않습니다. "
                f"Dict, Any, list 등을 피하고 전용 Pydantic 모델을 정의하여 사용하세요."
            )

    def _has_mcp_decorator(self, func_node: ast.AST) -> bool:
        """@mcp.tool() 또는 @mcp.tool 데코레이터 존재 여부 확인"""
        if not hasattr(func_node, 'decorator_list'):
            return False

        for deco in func_node.decorator_list:
            # 상황 A: @mcp.tool() (ast.Call)
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute):
                if getattr(deco.func.value, 'id', '') == 'mcp' and deco.func.attr == 'tool':
                    return True
            # 상황 B: @mcp.tool (ast.Attribute)
            elif isinstance(deco, ast.Attribute):
                if getattr(deco.value, 'id', '') == 'mcp' and deco.attr == 'tool':
                    return True
        return False

    def validate(self, data: Any):
        code_snippet = getattr(data, "code", "")
        if not code_snippet:
            raise ValueError("검증할 소스 코드가 비어 있습니다.")

        # ast.parse 시 문법 오류가 있으면 여기서 자동으로 SyntaxError 발생 -> 실패 처리
        tree = ast.parse(code_snippet)

        # 모든 함수(def, async def) 추출 후 mcp 데코레이터 필터링
        tool_functions = [
            n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and self._has_mcp_decorator(n)
        ]

        if not tool_functions:
            raise LookupError("생성된 코드에 @mcp.tool() 데코레이터가 붙은 함수가 없습니다.")

        # 모든 도구 함수의 반환 타입 전수 검사
        for target_func in tool_functions:
            if not target_func.returns:
                raise TypeError(f"도구 '{target_func.name}'에 반환 타입 힌트(->)가 누락되었습니다.")

            # 구체적인 모델인지 검사 (실패 시 내부에서 raise)
            self._check_concrete_type(target_func.returns, target_func.name)

        return data

@node(input=UserQuery, output=ToolPack)
class ItemCrawler(NodeV):

    def __init__(self):
        self.url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        super().__init__(validators=[ConcreteResultValidator()])

    def _extract_url(self, text: str) -> Optional[str]:
        """정규표현식을 이용한 URL 추출"""
        match = self.url_pattern.search(text)
        return match.group(0) if match else None

    async def run(self, **kwargs) -> Type[BaseModel]:
        query_str = kwargs.get('query', '')
        target_url = self._extract_url(query_str)

        # 1. URL이 없는 경우: LLM에게 상황을 전달하여 "URL 재요청" 응답을 유도
        if not target_url:
            raise ValueError("ERROR: No URL found in your query. Please provide a valid link.")

        kwargs['context'] = {'munge/text-from-url': await mcpc.call('munge/text-from-url',
                                                                    'extract_web_data',
                                                                    {'url': target_url})}
        # tools 스키마
        if 'tools' in kwargs:
            kwargs['tools'] = await mcpc.load_tools_spec(kwargs.get('tools'))

        return await super().run(**kwargs)

if __name__ == "__main__":
    async def test_run():
        crawler = ItemCrawler()
        # 질문 안에 URL이 섞여 있는 경우 테스트
        user_input = "https://finance.naver.com/item/coinfo.naver?code=005930 모든 정보 추출하라"

        try:
            result = await crawler.run(query=user_input, tools=['munge/text-from-url'])
            tools.dump(result)

            print("\n--- 분석 결과 (ToolPack) ---")
            print(json.dumps(result.model_dump(mode='json'), ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"최종 실패: {e}")

    asyncio.run(test_run())

    # async def run(self, **kwargs):
    #     tool = await super().run(**kwargs)
    #
    #     info(f'validating... tool_id: {tool.tool_id}')
    #     tools.dump(tool, "syntax-passed")
    #
    #     _, validated_tool = await tools.execute_with_fix(tool)
    #
    #     info(f'cooked... tool_id: {validated_tool.tool_id}, description: {validated_tool.description}')
    #     return validated_tool
