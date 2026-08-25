# Report Quality Rubric — release QA (도메인 공통)

release 는 draft `report_document` 를 **검수**한 뒤, junk·placeholder·수치 불일치·누락 블록만 patch 한다.
**한글 본문을 통째로 다시 쓰지 말 것.** 도메인 brief 체크리스트는 **추가** 항목으로만 사용.

## 구조 (필수)

- [ ] `layout.blocks[].key` 가 모두 `data` 에 존재
- [ ] `data[key].role` — executive_summary 또는 kpi_row 1개 이상
- [ ] `metrics_table` / `appendix_table` type 또는 table + role 1개 이상
- [ ] **각 table 직후** `insight_card` + `data.role: table_insight`
- [ ] `primary_chart` (또는 chart) 1개 이상, series 비어 있지 않음
- [ ] **각 chart 직후** `insight_card` + `data.role: chart_insight`
- [ ] **마지막 블록** `closing_card` + `data.role: conclusions` (차트·표로 종료 금지)
- [ ] 섹션·카드 제목에 `task-...` 등 내부 task_id 노출 없음

## 콘텐츠

- [ ] 리드: 모집단 + 핵심 발견 (고유명 + 숫자). 주어 없는 총평 금지
- [ ] table_insight / chart_insight: 항목명과 수치로 2~4문장. 「데이터가 보여줍니다」 금지
- [ ] conclusions: 계층 필요 시 **중첩 ordered list**
- [ ] markdown 볼드 카드당 1~2곳
- [ ] 집계 수치가 긴 card markdown 에만 있지 않음 (table 로 분리)
- [ ] placeholder·junk·`TODO`·`N/A` 남발 없음
- [ ] card title 과 content `##` 제목 중복 없음
- [ ] 한글 카드가 유니코드 공백으로 비어 있지 않음

## 수치 정합

- [ ] 본문 수치가 `llm_attach` upstream payload 와 일치
- [ ] table row 수·chart data point 가 upstream 과 모순 없음
- [ ] 표/차트에 데모 행이나 만 단위로 떨어지는 예시 수치가 **없음** — upstream 비면 빈 표

## 시각 품질 (visual_design)

- [ ] 차트 타입이 질문(비교/추세/구성/관계)에 맞음 — 특정 차트 형태 강제 아님
- [ ] chart `grid` 단일 object. `containLabel` 과 큰 left/top 을 같이 쓰지 않음
- [ ] 차트 안 제목 중복 없음 (`title.show=False`). 범례는 bottom (`legend.top` 없음)
- [ ] 축 눈금은 만/억 등 짧은 단위 + `hideOverlap`. 단위는 축 `name`
- [ ] table `header` 한글
- [ ] 차트·섹션 제목이 메시지형
- [ ] 양·음이 섞인 bar 에는 0선이 있으면 읽기 쉽다 (해당될 때만)

## 메타

- [ ] `template_id` 가 `analytical-standard` 또는 `financial-standard` (동일 패턴)
- [ ] `release_summary.changes[]` 에 patch 항목 기록, `task_id` 포함

## patch 우선순위

1. 누락 table_insight / chart_insight / closing_card(conclusions) 추가
2. layout 순서 — insight 직후 배치, conclusions 마지막
3. 수치·placeholder 정정
4. task_id 노출 제거·role 보강
5. `grid` 배열 → 단일 grid, table header 한글화, 축 라벨 겹침·범례 겹침 정정
6. 문체·중복 제목 정리
7. **하지 말 것**: 한글 카드 content/title 을 새 문자열로 재작성, 첨부 화면 레이아웃 복제
