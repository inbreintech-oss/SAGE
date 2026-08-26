import type {CSSProperties} from "react";
import {getThemePreset, type SageThemePresetId} from "@/design-tokens/mantine";

export type PreviewColorScheme = "light" | "dark";

/** 프리셋 CSS 변수를 인라인 style 객체로 변환 (미리보기 스코프용) */
export function getPresetStyleVars(
    id: SageThemePresetId,
    colorScheme: PreviewColorScheme = "light",
): CSSProperties {
    const {cssVariablesResolver} = getThemePreset(id);
    const resolved = cssVariablesResolver({} as never);
    const schemeVars = colorScheme === "dark"
        ? (resolved.dark ?? {})
        : (resolved.light ?? {});

    const merged: Record<string, string> = {
        ...resolved.variables,
        ...schemeVars,
    };
    return merged as CSSProperties;
}

export const PREVIEW_MENU = [
    {label: "대시보드", icon: "dashboard", active: true},
    {label: "데이터 분석 모델", icon: "database", section: "데이터"},
    {label: "보고서", icon: "report", section: "데이터"},
    {label: "보고서 목록", icon: "list", section: "데이터"},
    {label: "도구(Tool)", icon: "tool", section: "핵심 자산 설정"},
] as const;

export const PREVIEW_TABS = ["홈", "데이터", "보고서", "도구"] as const;
