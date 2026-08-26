import {createTheme, type CSSVariablesResolver} from "@mantine/core";
import type {SageThemePreset} from "./types";
import {FONT_FAMILY, FONT_MONO, sageBlue, sageSlate, sageTeal, sageZinc} from "./sharedColors";

const theme = createTheme({
    fontFamily: FONT_FAMILY,
    fontFamilyMonospace: FONT_MONO,
    primaryColor: "sageTeal",
    primaryShade: 6,
    defaultRadius: "sm",
    colors: {
        sageTeal,
        sageBlue,
        sageSlate,
        sageZinc,
    },
    other: {
        layoutTopbarHeight: 48,
        layoutNavWidth: 240,
        layoutPanelLeftWidth: 280,
        layoutPanelRightWidth: 360,
    },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
    variables: {
        "--sage-font-mono": FONT_MONO,
        /** Dark command top bar */
        "--sage-topbar-bg": "#18181b",
        "--sage-topbar-bg-hover": "#27272a",
        "--sage-topbar-text": "#fafafa",
        "--sage-topbar-text-muted": "#a1a1aa",
        "--sage-topbar-border": "#27272a",
        /** Light secondary nav */
        "--sage-nav-bg": "#fafafa",
        "--sage-nav-bg-hover": "#f4f4f5",
        "--sage-nav-bg-active": "#f0fdfa",
        "--sage-nav-text": "#71717a",
        "--sage-nav-text-hover": "#18181b",
        "--sage-nav-text-active": "#0d9488",
        "--sage-nav-active-indicator": "#0d9488",
        /** Page & panels */
        "--sage-page-bg": "#f4f4f5",
        "--sage-surface-panel": "#ffffff",
        "--sage-surface-code": "#f8fafc",
        "--sage-border-color": "#e4e4e7",
        "--sage-border-active": "#0d9488",
        "--sage-input-border": "#e4e4e7",
        "--sage-focus-ring": "#0d9488",
        /** Brand */
        "--sage-brand-primary": "#0d9488",
        "--sage-brand-primary-hover": "#0f766e",
        "--sage-brand-primary-subtle": "#ccfbf1",
        "--sage-brand-secondary": "#0090da",
        /** Status */
        "--sage-status-running": "#22c55e",
        "--sage-status-pending": "#f59e0b",
        "--sage-status-failed": "#ef4444",
        "--sage-status-idle": "#a1a1aa",
        /** Category icon colors */
        "--sage-category-data": "#0d9488",
        "--sage-category-report": "#2563eb",
        "--sage-category-tool": "#ea580c",
        "--sage-category-dashboard": "#7c3aed",
        /** Layout dimensions */
        "--sage-layout-topbar-height": "48px",
        "--sage-layout-nav-width": "240px",
        "--sage-layout-page-title-height": "44px",
        "--sage-layout-panel-left-width": "280px",
        "--sage-layout-panel-right-width": "360px",
        /** Component */
        "--sage-button-radius": "6px",
        "--sage-card-radius": "8px",
    },
    light: {
        "--mantine-color-text": "#3f3f46",
    },
    dark: {
        "--mantine-color-text": "#fafafa",
    },
});

export const commandCenterPreset: SageThemePreset = {
    id: "command-center",
    label: "Command Center",
    description: "Dark Top Bar + Light Secondary Nav — Grafana/Metabase 스타일",
    theme,
    cssVariablesResolver,
    figmaTokensPath: "figma/command-center.tokens.json",
};
