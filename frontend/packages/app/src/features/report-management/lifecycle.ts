/** 보고서 관리 UI 상태 머신 */

export type ReportLifecycle = "drafting" | "completed" | "published" | "viewing";

export type PanelLayout = {
    leftOpen: boolean;
    centerOpen: boolean;
    rightOpen: boolean;
};

export function derivePanelLayout(lifecycle: ReportLifecycle): PanelLayout {
    switch (lifecycle) {
        case "drafting":
            return { leftOpen: true, centerOpen: true, rightOpen: false };
        case "completed":
            /* 뷰어는 Print Preview Modal — 작업 화면은 목록+작성 */
            return { leftOpen: true, centerOpen: true, rightOpen: false };
        case "published":
            return { leftOpen: true, centerOpen: true, rightOpen: false };
        case "viewing":
            return { leftOpen: true, centerOpen: true, rightOpen: false };
        default:
            return { leftOpen: true, centerOpen: true, rightOpen: false };
    }
}

export function isCenterReadonly(lifecycle: ReportLifecycle): boolean {
    return lifecycle === "published" || lifecycle === "viewing";
}

export function canShowPublishButton(lifecycle: ReportLifecycle): boolean {
    return lifecycle === "completed";
}

export function canShowGenerateButton(lifecycle: ReportLifecycle): boolean {
    return lifecycle === "drafting" || lifecycle === "completed";
}

export function canShowOutputButton(lifecycle: ReportLifecycle): boolean {
    return lifecycle === "viewing";
}

/** 등록 전(generate 완료) 미리보기 — API status completed 구간 */
export function canReopenPreview(
    lifecycle: ReportLifecycle,
    hasReport: boolean,
): boolean {
    return hasReport && lifecycle === "completed";
}

export function canEditDraft(lifecycle: ReportLifecycle): boolean {
    return lifecycle === "drafting" || lifecycle === "completed";
}
