# ECharts (visual chart key)

[[report/visual_design]]

[[report/insight_craft]]

Option 객체를 **그대로** 저장 (`{type:echarts}` 래퍼 금지).

**Python codegen**: 아래 예시의 `true`/`false`/`null` 을 **그대로 쓰지 말 것** — dict 리터럴에는 `True`/`False`/`None` 사용.

**필수**: `title.text`, `tooltip`, **`grid` 단일 object** (`containLabel=True`)

**금지 (차트 미표시)**: `grid` 를 `[{...},{...}]` 배열로 두지 말 것. `gridIndex` 로 패널을 나누지 말 것.

**금지 (글자 겹침·치우침)**:
- 차트 안 `title.show=True` — 카드가 이미 제목을 그린다. **`title.show=False`**
- `title.subtext` 로 단위를 쓰지 말 것 — 범례와 겹침. value 축 `name` 에 단위
- `containLabel=True` 인데 `left`/`top` 을 80 이상으로 두지 말 것 — 플롯이 한쪽으로 밀린다
- `legend.top` — 제목·시리즈명과 겹친다. 범례는 `bottom` 만 (`top` 키 자체 금지)
- 축 눈금에 `1,000,000` 단위 원숫자. 값을 만/억으로 나눠 넣고 축 `name` 에 단위
- `splitNumber` 를 크게 두지 말 것 (4~5). `axisLabel.hideOverlap=True`

차트 **타입은 질문**에 맞춘다 (비교 / 추세 / 구성 / 관계). 양·음 상대 비교일 때만 가로 그룹 bar + 0선이 적합하다.

`yAxis.data`·`series[].data` 는 upstream 집계 (리터럴 금지). 색은 잉크 팔레트 (`#1B4D6E`, `#2A9D8F`).

```python
{
    "backgroundColor": "#FFFFFF",
    "color": ["#1B4D6E", "#2A9D8F"],
    "title": {
        "text": "지역별 매출 비교",
        "show": False,
        "textStyle": {
            "color": "#1A1F2E",
            "fontWeight": 600,
            "fontSize": 15,
            "fontFamily": "Noto Sans KR, Pretendard, sans-serif",
        },
    },
    "legend": {
        "bottom": 0,
        "left": "center",
        "type": "scroll",
        "textStyle": {"color": "#5C6578"},
    },
    "tooltip": {
        "trigger": "axis",
        "confine": True,
        "axisPointer": {"type": "shadow"},
        "backgroundColor": "#1A1F2E",
        "borderWidth": 0,
        "textStyle": {"color": "#F6F3EC"},
    },
    "grid": {
        "containLabel": True,
        "left": 16,
        "right": 16,
        "top": 16,
        "bottom": 48,
    },
    "xAxis": {
        "type": "value",
        "name": "억 원",
        "splitNumber": 5,
        "axisLabel": {
            "color": "#5C6578",
            "hideOverlap": True,
        },
        "axisLine": {"show": False},
        "splitLine": {
            "show": True,
            "lineStyle": {"type": "dashed", "color": "#EEEEEE"},
        },
    },
    "yAxis": {
        "type": "category",
        "data": region_names,  # upstream ranking
        "inverse": True,
        "axisTick": {"show": False},
        "axisLabel": {
            "color": "#5C6578",
            "hideOverlap": True,
            "overflow": "truncate",
            "width": 88,
        },
        "axisLine": {"lineStyle": {"color": "#C8C2B6"}},
    },
    "series": [
        {
            "name": "매출",
            "type": "bar",
            "data": sales_values,  # 억 원으로 나눈 값
            "itemStyle": {"color": "#1B4D6E"},
        },
    ],
}
```

시계열: `line` (`smooth=False`, `symbol="circle"`, `symbolSize=6`) 또는 bar+line 콤보.
도넛(구성, 조각 ≤6): `radius=["42%", "62%"]`.
양·음이 섞인 상대값: 가로 그룹 bar + `markLine` `{xAxis: 0}` + 범례. 값>0 `#2F6F5E` / 값<0 `#A63D40` (단일 시리즈).
