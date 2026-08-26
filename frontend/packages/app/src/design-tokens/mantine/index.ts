import type {SageThemePreset, SageThemePresetId} from "./types";
import {commandCenterPreset} from "./themeCommandCenter";
import {lightShellPreset} from "./themeLightShell";
import {recommendedPreset} from "./themeRecommended";
import {workspaceTabsPreset} from "./themeWorkspaceTabs";

export type {SageThemePreset, SageThemePresetId} from "./types";
export {lightShellPreset} from "./themeLightShell";
export {commandCenterPreset} from "./themeCommandCenter";
export {recommendedPreset} from "./themeRecommended";
export {workspaceTabsPreset} from "./themeWorkspaceTabs";
export {
    sageBlue,
    sageTeal,
    sageIndigo,
    sageSlate,
    sageZinc,
    sageGray,
    FONT_FAMILY,
    FONT_MONO,
} from "./sharedColors";

/** 등록된 모든 테마 프리셋 */
export const SAGE_THEME_PRESETS: Readonly<Record<SageThemePresetId, SageThemePreset>> = {
    "light-shell": lightShellPreset,
    "command-center": commandCenterPreset,
    "workspace-tabs": workspaceTabsPreset,
    "recommended": recommendedPreset,
};

/** ID로 테마 프리셋 조회 (기본값: recommended) */
export function getThemePreset(id: SageThemePresetId = "recommended"): SageThemePreset {
    return SAGE_THEME_PRESETS[id];
}

/** Figma token path → CSS variable 매핑 (공통 키) */
export const FIGMA_TO_CSS_MAP: Readonly<Record<string, string>> = {
    "color.surface.page": "--sage-page-bg",
    "color.surface.nav": "--sage-nav-bg",
    "color.surface.nav-hover": "--sage-nav-bg-hover",
    "color.surface.nav-active": "--sage-nav-bg-active",
    "color.surface.topbar": "--sage-topbar-bg",
    "color.surface.card": "--sage-surface-card",
    "color.surface.panel": "--sage-surface-panel",
    "color.text.primary": "--mantine-color-text",
    "color.text.nav-active": "--sage-nav-text-active",
    "color.text.nav-default": "--sage-nav-text",
    "color.border.default": "--sage-border-color",
    "color.border.focus": "--sage-focus-ring",
    "color.border.input": "--sage-input-border",
    "color.brand.primary": "--sage-brand-primary",
    "color.brand.primary-hover": "--sage-brand-primary-hover",
    "color.brand.primary-subtle": "--sage-brand-primary-subtle",
    "layout.topbar-height": "--sage-layout-topbar-height",
    "layout.nav-width": "--sage-layout-nav-width",
    "layout.rail-width-collapsed": "--sage-layout-nav-width",
    "layout.rail-width-expanded": "--sage-layout-nav-width-expanded",
    "layout.context-panel-width": "--sage-layout-context-panel-width",
    "radius.md": "--sage-button-radius",
    "radius.lg": "--sage-card-radius",
};
