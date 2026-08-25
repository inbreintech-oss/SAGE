from sage.models.node import DataAnalysisInput, DataAnalysisOutput
from sage.nodes import node, NodeV

@node(input=DataAnalysisInput, output=DataAnalysisOutput)
class DataAnalyzer(NodeV):
    """
    불완전한 소스 메타데이터를 분석하여
    통합 메타 데이터를 생성
    """
