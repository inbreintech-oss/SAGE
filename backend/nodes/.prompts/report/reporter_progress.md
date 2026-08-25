# Reporter progress (사용자 화면)

메시지는 **서비스 사용자 화면**에 그대로 노출된다. 노드마다 호출 API 가 다르다.

## report 태스크 (`run_task`)

```python
async def run_task(task, ctx, reporter=None):
    safe_report(reporter, "[단계] 구체 메시지", state="running")   # O
    # await safe_report(...)   # X 금지
```

## pangeaze unify.py — `safe_report` 금지, `except Exception` 금지

report 태스크 패턴을 unify 에 복사하지 말 것.

```python
if reporter:
    reporter.update("[조회] 종목 정보 (3/100)", state="running")
```

- `[데이터]` `[조회]` `[분석]` `[차트]` 등 단계 태그 + 구체 한글
- **완성형 한글만** (NFC). 자모를 풀어 쓰지 말 것 (`ㅈㅗㅎㅚ` 금지 → `조회`)
- 화면 문구 오타 금지: `정보` `완료` `외국인` `기관` `통합` — `정버` `관료` `애국인` `투갬` 금지
- task_id, model명, MCP 함수명, TaskContext, upstream 등 **내부 용어 금지**
