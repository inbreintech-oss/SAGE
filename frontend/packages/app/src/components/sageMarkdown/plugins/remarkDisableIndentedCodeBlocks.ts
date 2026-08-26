/**
 * remark 플러그인: 4스페이스 들여쓰기 → code block 변환 비활성화
 *
 * CommonMark에서는 4개 이상의 스페이스로 시작하는 줄을 indented code block으로 파싱한다.
 * LLM이 생성한 콘텐츠에서 들여쓰기가 의도치 않게 code block으로 렌더되는 문제를 방지한다.
 * micromark의 codeIndented 구문 자체를 파서 레벨에서 비활성화한다.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function remarkDisableIndentedCodeBlocks(this: any) {
    const data = this.data()
    if (!data.micromarkExtensions) data.micromarkExtensions = []
    data.micromarkExtensions.push({ disable: { null: ['codeIndented'] } })
}
