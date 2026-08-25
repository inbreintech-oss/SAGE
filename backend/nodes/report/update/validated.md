
## [RUNTIME_ERROR]
- **최근 업데이트**: 2026-05-27 10:14:23
발생한 오류 `KeyError: 0`은 `caller.py`의 72행 `top_industry = analysis_res[0]['industry']`에서 발생했습니다. 파이썬에서 리스트의 범위를 벗어날 경우 `IndexError`가 발생하지만, **`KeyError: 0`이 발생했다는 것은 `analysis_res`가 리스트가 아니라 딕셔너리(dict) 형태**로 반환되었거나, 예상과 다른 데이터 구조를 가지고 있음을 의미합니다.

### 1. 오류 원인 분석

1.  **데이터 타입 불일치**: `analysis_res = await call(...)`를 통해 받은 결과가 `List[GapResult]` 형태가 아니라, MCP 서버의 응답 명세에 따라 특정 키(예: `{'result': [...]}`)를 가진 딕셔너리이거나, 빈 딕셔너리일 가능성이 큽니다.
2.  **빈 결과 값**: 만약 `metrics_input`이 비어 있거나 도구가 빈 리스트를 반환했을 때, 이에 대한 방어 로직 없이 `[0]` 인덱스로 접근하려 했습니다.
3.  **MCP 호출 특성**: 일부 MCP 환경에서는 도구의 실행 결과가 직접 반환되지 않고, 래핑된 객체 형태로 반환될 수 있는데, 이를 리스트로 간주하고 인덱싱을 시도할 때 발생합니다.

---

### 2. 향후 재발 방지를 위한 통합 교정 지침

데이터 분석 도구 및 Caller 작성 시 다음의 지침을 반드시 준수하여 런타임 안정성을 확보하십시오.

#### [지침 1: 도구 결과값의 유효성 및 타입 검증]
*   도구 호출(`call`) 이후의 결과값은 반드시 **타입 검증(isinstance)**과 **길이 검증(len)**을 거친 후 인덱싱을 수행한다.
*   **교정 전:** `top_industry = analysis_res[0]['industry']`
*   **교정 후:**
    ```python
    if isinstance(analysis_res, list) and len(analysis_res) > 0:
        top_industry = analysis_res[0].get('industry', 'N/A')
    else:
        # 리스트가 아니거나 비어있을 경우의 예외 처리
        return {"content": "분석 결과 데이터가 없거나 형식이 올바르지 않습니다."}
    ```

#### [지침 2: 입력 데이터 부재에 대한 사전 차단]
*   도구를 호출하기 전, 입력 파라미터(`metrics_input` 등)가 비어 있는지 확인하여 불필요한 도구 호출과 잠재적 오류를 방지한다.
*   **적용:**
    ```python
    if not metrics_input:
        return {"content": "분석을 위한 유효한 업종별 데이터가 부족하여 분석을 진행할 수 없습니다."}
    ```

#### [지침 3: 딕셔너리 접근 시 `.get()` 메서드 활용]
*   결과 데이터 내의 특정 키에 접근할 때 `obj['key']` 대신 `obj.get('key', default)`를 사용하여 키 부재로 인한 런타임 에러를 방지한다.

#### [지침 4: 상세 에러 로깅 및 피드백]
*   도구 실행 실패 시 단순히 "오류가 발생했습니다"라고 출력하기보다, 어떤 단계(데이터 로드, 필터링, 도구 호출 등)에서 문제가 생겼는지 구체적인 메시지를 반환하도록 구성한다.

---

### 3. 수정된 caller.py (핵심 부분)

오류가 발생한 `caller.py`의 로직을 다음과 같이 안전하게 수정해야 합니다.

```python
      # 5. 분석 도구 호출
      analysis_res = await call(
          "tm-industry-gap-analyzer-b9a2c1d0",
          "calculate_valuation_gaps",
          {"request": {"metrics": metrics_input}}
      )

      # [수정] 결과 타입 및 데이터 존재 여부 검증
      if not analysis_res or not isinstance(analysis_res, list):
          return {"content": "업종별 격차 분석 결과가 유효하지 않거나 데이터를 생성할 수 없습니다."}

      # 6. 시각화(Vega-Lite) 및 결과 구성
      chart_data = analysis_res
      
      # [수정] 인덱스 접근 전 안전 확인
      if len(chart_data) > 0:
          # dict 형태인지 확인하며 안전하게 추출
          first_item = chart_data[0]
          top_industry = first_item.get('industry', '알 수 없음')
          top_index = first_item.get('valuation_index', 0)
      else:
          return {"content": "조건에 부합하는 분석 결과가 존재하지 않습니다."}

      chart_spec = {
          "title": "업종별 저평가 종목군 밸류에이션 격차 지수",
          "mark": "bar",
          "encoding": {
              "x": {"field": "industry", "type": "nominal", "title": "업종", "axis": {"labelAngle": 45}},
              "y": {"field": "valuation_index", "type": "quantitative", "title": "가치 격차 지수 (Index)"},
              "color": {"field": "valuation_index", "type": "quantitative", "scale": {"scheme": "greens"}}
          },
          "data": {"values": chart_data}
      }

      content = (
          f"저평가 종목군이 속한 주요 업종을 대상으로 전체 평균 대비 가치 격차를 분석한 결과, "
          f"**{top_industry}** 업종이 지수 **{top_index}**로 가장 높은 상대적 저평가 매력을 나타냈습니다.\n\n"
          f"[[industry_gap_chart]]"
      )
```

이 지침을 적용하면 데이터가 없거나 도구가 예상치 못한 구조를 반환하더라도 시스템 전체가 중단되지 않고 사용자에게 명확한 피드백을 줄 수 있습니다.
---