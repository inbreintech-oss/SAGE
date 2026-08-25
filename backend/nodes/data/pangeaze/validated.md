## [RUNTIME_ERROR]
- **최근 업데이트**: 2026-07-08 09:14:29
### 런타임 오류 원인 분석 및 해결 방안
1. **오류 원인**: `InMemoryDataBridge.get` 함수가 반환하는 `file_data`는 **pandas DataFrame** 객체입니다. 이를 `FileStockAdapter.transform` 내부에서 직접 순회(`for row in data:`)하면 각 행(Row) 대신 **컬럼명(문자열)**이 순회 변수 `row`에 담겨 `'str' object has no attribute 'get'` 예외가 발생했습니다.
2. **해결 방법**: `adapter.py` 내의 모든 어댑터 `transform` 메서드가 DataFrame 입력을 안전하게 처리할 수 있도록 `isinstance(data, pd.DataFrame)`를 검사하여 `data.to_dict(orient="records")`로 자동 변환 후 순회하도록 보완했습니다.
---
```json
{
  "metadata": {
    "sources": [
      {
        "id": "src-b754c764",
        "type": "file",
        "path": "stocks10.csv",
        "adapter": "FileStockAdapter"
      },
      {
        "id": "src-721710db",
        "type": "tool",
        "tool_path": "kis/stock",
        "adapter": "KisStockAdapter"
      }
    ],
    "targets"
...(truncated; see instruction.md)
---
## [ModuleNotFoundError]
- **최근 업데이트**: 2026-07-24 16:32:01
### [ModuleNotFoundError] (runtime) 재시도 후 통과
* **원인**: ModuleNotFoundError: No module named 'google'
* **준수 계약**: instruction.md + runtime_contract
* **수정**: 위 계약·validator 오류 메시지를 그대로 반영해 동일 contract 위반 금지
---

## [PydanticValidator]
- **최근 업데이트**: 2026-08-22 18:41:00
### [PydanticValidator] (codegen) 반복 주의
* **원인**: unify.py 에 `except Exception` 이 있으면 계약 실패. reporter 용 try/except·safe_report 도 동일.
* **수정**: `except Exception` 검색 0건. `if reporter: reporter.update(...)`. `await call` 은 try 없이.
* **준수 계약**: instruction.md + 입력 소스 가이드 (FILE_SOURCE_IDS = 파일 source_id)
---