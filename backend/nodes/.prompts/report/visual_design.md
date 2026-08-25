# 보고서 시각 품질 (상용 분석 보고서)

목표는 **리서치 데스크 한 장**이다. 기본 ECharts 파랑 막대·무지개 파이·「분석 차트」 제목은 쓰지 않는다.
수치는 정확하되, **한눈에 비교·추세·구성·관계가 읽히게** 표현한다.

인사이트 밀도는 [[report/insight_craft]]. 아래 팔레트·차트 타입은 **가이드**다. 첨부 화면을 복제하지 말 것.

## 톤 (잉크 · 절제된 액센트)

흰 지면 + 포인트 1~2곳. 원색·네온·그라데이션 남발 금지.

| 역할 | hex / 토큰 | 쓰임 |
|------|------------|------|
| 잉크 | `#1A1F2E` / `ink` | 제목, 본문 핵심, 축 이름 |
| 슬레이트 | `#5C6578` / `muted` | 보조 라벨, 범례, 축 눈금 |
| 페이퍼 | `#FFFFFF` | 차트 배경 |
| 네이비 | `#1B4D6E` / `primary` | 1st series |
| 틸 | `#2A9D8F` | 2nd series (비교가 있을 때) |
| 골드 | `#C4A35A` / `gold` | 섹션 강조·핵심 하이라이트 1곳 |
| 포지티브 | `#2F6F5E` / `success` | 단일 시리즈 양(+) |
| 네거티브 | `#A63D40` / `danger` | 단일 시리즈 음(−) |
| 3rd series | `#4A6FA5` | 세 번째 시리즈 |
| 그리드 | `#EEEEEE` | value 축 점선 |

`data.style.accent` 는 **토큰명** (`ink`, `primary`, `gold`, `success`, `danger`, `muted`) 만.

## 섹션·카드 강조

`data[key].style` 로 렌더 힌트를 준다. **모든 블록에 highlight 금지.**

| 블록 | style | 의도 |
|------|-------|------|
| `document_title` | `variant=emphasis`, `accent=ink`, `density=spacious` | 표지 타이틀 |
| `section_title` | `variant=emphasis`, `accent=gold`, `border=true` | 섹션 구분 |
| `summary_card` | `variant=callout`, `accent=muted` | 리드 박스 |
| `kpi_card` | `variant=emphasis`, `density=compact` | 숫자 우선 |
| 핵심 `insight_card` **최대 1개** | `variant=highlight`, `accent=gold` | 코어 한 줄 (있을 때만) |
| 그 외 insight | `variant=default` | 과잉 강조 방지 |
| `closing_card` | `variant=emphasis`, `accent=ink` | 결론 |
| `metrics_table` | `density=compact`, `border=true` | 타이트한 지표 표 |

볼드(`**`)는 카드당 **핵심 1곳**. 수치 전량 볼드 금지.

## 차트 선정 (데이터 특성 → 타입)

단순 bar/pie 기본값 금지. **질문이 뭔지**에 맞춰 고른다.

| 데이터 특성 | 선호 차트 | 피하기 |
|-------------|-----------|--------|
| 카테고리 다수 × 주체 2개 × 상대값(±) | 가로 그룹 bar + 0선 + 범례 | 세로 bar 5개, 파이 |
| 시계열·추세 | `line` 또는 bar+line 콤보 | 파이 |
| 부호 있는 단일 시리즈 | 가로 bar, 양/음 이색 | 단색 세로 bar |
| 카테고리 랭킹 (1지표) | 가로 bar, 라벨 전체 | 항목 많은 세로 bar |
| 구성·비중 (≤6조각) | 도넛 `pie` `radius=["42%","62%"]` | 조각 많은 파이 |
| 구성 시계열 | stacked bar 또는 100% stacked | 파이 나열 |
| 두 지표 관계 | `scatter` | 무의미 bar |
| 행렬·상관 | `heatmap` | 숫자 표만 |
| 기여도·증감 분해 | waterfall 또는 stacked bar | 단일 총액 bar |

한 차트 = **한 메시지**. 시리즈 4개 넘으면 쪼개거나 상위 N + 기타.
비교가 목적인데 카테고리를 5개로 자르지 말 것. 그룹이 10개면 10개다. 없는 항목을 채워 넣지 말 것.

## ECharts 표현 (Option에 직접)

색은 Option `color` / `itemStyle` 에 hex 로 넣는다.

- `color`: `["#1B4D6E", "#2A9D8F", "#4A6FA5", "#C4A35A"]` — 시리즈 순
- `backgroundColor`: `"#FFFFFF"` 또는 생략
- `title.text` 필수. **`title.show: False`** — 보고서 카드가 제목을 그리므로 차트 캔버스에 같은 제목을 다시 그리지 말 것 (중복·여백 치우침)
- 단위는 `title.subtext` 가 아니라 value 축 **`name`** (`만 주`, `억 원`). subtext+범례가 한 줄에 겹친다
  `textStyle` `{color:"#1A1F2E", fontWeight:600, fontSize:15, fontFamily:"Noto Sans KR, Pretendard, sans-serif"}`
- `legend`: 시리즈 2개+ 일 때. **`bottom: 0`**, `left: "center"`, `type: "scroll"`. **`legend.top` 키를 넣지 말 것** (넣으면 제목·시리즈명과 겹침)
- `tooltip`: `trigger` 맞는 값, `confine: True`, `backgroundColor="#1A1F2E"`, `borderWidth=0`, `textStyle.color="#F6F3EC"`
- `grid`: **단일 object**. **배열 금지**
  - `containLabel: True` 이면 `left/right/top` 은 **12~24**. 큰 `left`(80+) 와 같이 쓰면 플롯이 오른쪽 아래로 밀린다
  - `containLabel: False` 일 때만 한글 카테고리용 `left` 88~120
  - 범례가 아래면 `bottom` 48~64
- `xAxis`/`yAxis`: 기본은 **각각 단일 object**. 이중 Y축만 `yAxis` 배열 2개(같은 grid)
- 가로 랭킹 bar: `xAxis.type=value`, `yAxis.type=category`, `yAxis.inverse=True`(위→아래)
- **축 숫자 겹침 금지**: `-4,000,000` 같은 긴 눈금 금지. series 값을 **만·억** 으로 나눠 넣고 축 `name` 에 단위. `splitNumber` 4~5, `axisLabel.hideOverlap: True`
- value 축 `splitLine`: 점선 `#EEEEEE`. 양·음이 섞이면 series `markLine` 0선 — 실선 `#9AA0A6`
- 양/음 **단일** 바: 값 부호로 `#2F6F5E` / `#A63D40`
- **금지**: `grid` 배열, `gridIndex`, 3D, 무지개 10색, `label.formatter` 하드코딩 리터럴, `containLabel`+과도한 `left`/`top` 동시
- 비교는 **한 grid 에 시리즈 그룹** 또는 차트 2개. 프론트는 `grid` 배열을 접어 **차트가 안 보인다**.

Python dict 에는 `True`/`False`/`None`.

## 표

- 컬럼 순서: 식별 → **핵심 지표** → 보조
- `header` 는 **한글 표시 라벨**
- `data[]`·`dtypes` 키는 영문, 권장 `columns: [{key,label}]`
- 표 `title` 로 무엇의 표인지
- 차트와 같은 집계를 표로 반복해 숫자를 읽게 할 것
- 길면 appendix 로 분리 — 비교가 목적인데 상위 5행만 남기지 말 것
- 숫자 정렬·소수 자릿수 통일 (`dtypes.decimals`)

## 카피 톤

제목은 명사구·사실. `"분석 차트"`, `"시각화 결과"` 금지.
insight 첫 문장: **고유명 + 숫자 + 방향**.
