from sage.models.node import DataExecutionInput, DataAnalysisOutput
from sage.nodes import node, NodeV

@node(input=DataExecutionInput, output=DataAnalysisOutput)
class DataExecutor(NodeV):
    """
    사용자 컨펌한 통합 스미카를 참고하여,
    통합 데이터 규격(schema.py)과 가공 로직(unify.py)을 생성하는 노드
    """
