## [ConcreteResultValidator]
- **최근 업데이트**: 2026-04-01 16:54:11
1. 규칙: 도구 반환 타입에 Dict, Any 등 범용 타입을 사용하지 말고 반드시 Pydantic BaseModel을 상속받은 전용 구조체 모델을 정의하여 명시할 것.
2. 예시:
Bad:
def parse_stock_info(symbol: str) -> Dict[str, Any]:
Good:
class StockData(BaseModel):
    symbol: str
    price: float
def parse_stock_info(symbol: str) -> StockData:
---

## [PydanticValidator]
- **최근 업데이트**: 2026-04-02 16:01:11
1. 규칙: Python f-string이나 멀티라인 문자열 사용 시, 내부의 하이픈(`-`)이나 특수문자가 줄 첫머리(Column 1)에 오지 않도록 들여쓰기를 강제하거나 문자열 결합 방식(`f"" f""`)을 사용할 것.

*   **Good**: 
    ```yaml
    code: |
        content = (
            f"- item1\n"
            f"- item2"
        )
    ```
*   **Bad**:
    ```yaml
    code: |
        content = f"""
    - item1
    - item2
        """
    ``` (줄 첫머리에 `-`가 위치하여 YAML 파서가 블록 종료로 오인함)
---