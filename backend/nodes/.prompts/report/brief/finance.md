# 작업 지시서: 금융·주식 데이터 분석 보고서

`default` 범용 outline 을 따르되, 아래 금융 도메인 보강을 적용합니다.

## 도메인 보강 (금융·주식)
- 밸류에이션: PER, PBR, EPS, ROE 등 dataset fields 에 있을 때만 서술
- 섹터·동종 비교: upstream 집계에 sector/group 필드가 있을 때
- 투자 의견: query 가 요구할 때만, 근거·리스크·한계 명시

## 금지
- dataset 에 없는 재무 지표를 임의 도입
- 종목·티커 literals 하드코딩
