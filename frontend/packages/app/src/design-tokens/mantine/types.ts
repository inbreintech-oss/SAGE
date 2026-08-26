import type {CSSVariablesResolver, MantineThemeOverride} from "@mantine/core";

/** 레이아웃 테마 프리셋 ID */
export type SageThemePresetId =
    | "light-shell"
    | "command-center"
    | "workspace-tabs"
    | "recommended";

/** Mantine 테마 + CSS 변수 리졸버 묶음 */
export type SageThemePreset = Readonly<{
    id: SageThemePresetId;
    label: string;
    description: string;
    theme: MantineThemeOverride;
    cssVariablesResolver: CSSVariablesResolver;
    /** Figma tokens JSON 상대 경로 (design-tokens 기준) */
    figmaTokensPath: string;
}>;
