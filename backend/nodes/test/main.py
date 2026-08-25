import ast
from typing import Any, Tuple, Optional

from pydantic import BaseModel, Field

from sage.nodes import NodeV, node, BaseValidator

class Query(BaseModel):
    query: str

class Result(BaseModel):
    answer: float
    answer_code: str = Field(description="평균을 구하기 위해 작성된 파이썬 코드")

class PythonSyntaxValidator(BaseValidator):
    """생성된 파이썬 코드의 문법적 유효성 검증"""

    def validate(self, data: Any):
        code = getattr(data, "answer_code", str(getattr(data, "answer", data)))
        ast.parse(code)
        return data

class MeanLogicValidator(BaseValidator):
    """실제 계산 결과가 산술적으로 타당한지 검증"""

    def validate(self, data: Any):
        if data.answer <= 0:
            raise ValueError("평균값이 0 이하일 수 없음")
        return data

@node(input=Query, output=Result)
class Test(NodeV):
    def __init__(self):
        validators = [
            PythonSyntaxValidator(),
            MeanLogicValidator()
        ]
        super().__init__(validators=validators)

if __name__ == '__main__':
    import asyncio

    t = Test()
    res = asyncio.run(t.run(query='배열을 이용해 평균을 내는 도구를 만들어라, ex. 3, 5, 1'))
    print(res)
