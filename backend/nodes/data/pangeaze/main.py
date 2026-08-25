import asyncio
import json

import sage.mcp as mcpc
from sage.models.node import DataAnalysisInput, PangeaOutput, ToolSourceMetadata, FileSourceMetadata
from sage.nodes import node, NodeV

@node(input=DataAnalysisInput, output=PangeaOutput)
class DataPangeazer(NodeV):
    """
    불완전한 소스 메타데이터를 분석하여
    PangeaDataFrame 관련 데이터를 생성
    """

async def test_pangeazer_with_tool():
    # 1. 파일 소스: 종목 기초 리스트 (CSV 가정)

    # source_csv = FileSourceMetadata(
    #     source_id="src_stock_list",
    #     path="stock.csv",
    #     file_format="csv",
    #     columns=["basDt", "srtnCd", "itmsNm"],
    #
    #     sample_data=[
    #         {"basDt": "20260422", "srtnCd": "005930", "itmsNm": "삼성전자"},
    #         {"basDt": "20260422", "srtnCd": "000020", "itmsNm": "동화약품"}
    #     ]
    # )
    # 2. 도구 소스: KIS 주식 상세 정보 (API)
    # 실제 kis/stock 도구의 입력 인자와 출력 구조를 분석 대상으로 전달
    source_tool = ToolSourceMetadata(
        source_id="kis_detail",
        tool_path="kis/stock",
        tool_spec=await mcpc.load_tools_spec(["kis/stock"])
        # {
        #     "tool_name": "get_stock_item_detail",
        #     "description": "주식 종목의 상세 재무 정보를 조회합니다.",
        #     "args": {
        #         "itcode": "string (종목코드)"
        #     },
        #     "output_example": {
        #         "per": "15.4",
        #         "pbr": "1.2",
        #         "eps": "5000",
        #         "name": "삼성전자"
        #     }
        # }
    )

    # 3. 노드 호출 (AnalysisInput 데이터 구성)
    print("--- [Pangeazer] 노드 실행 시작 (Tool 연동 테스트) ---")

    # DataAnalysisInput 인스턴스 생성
    test_input = DataAnalysisInput(
        dataset_name="StockFinancialAnalysis",
        user_query=(
            "kis/stock 도구만으로 per/pbr·일자 시세 데이터 구축. "
            "파일 없음. 질의에 맞게 종목을 선정해 도구를 호출할 것."
        ),
        sources=[source_tool]
    )

    try:
        pangzer = DataPangeazer()
        # 노드 실행
        result: PangeaOutput = await pangzer.run(**test_input.model_dump())

        # 4. 결과 출력
        print("\n--- [2] schema_code (Python) ---")
        print(result.schema_code)

        print("\n--- [1] metadata (JSON) ---")
        print(json.dumps(result.metadata, indent=2, ensure_ascii=False))

        print("\n--- [3] adapter_code (Python) ---")
        print(result.adapter)

        print("\n--- [4] unify_code (Python) ---")
        print(result.unify_logic_code)

    except Exception as e:
        print(f"!! 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_pangeazer_with_tool())
