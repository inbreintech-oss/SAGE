import {createTheme, type CSSVariablesResolver} from "@mantine/core";
import type {SageThemePreset} from "./types";
import {FONT_FAMILY, FONT_MONO, sageBlue, sageGray, sageSlate} from "./sharedColors";

const theme = createTheme({
    fontFamily: FONT_FAMILY,
    fontFamilyMonospace: FONT_MONO,
    primaryColor: "sageBlue",
    primaryShade: 7,
    defaultRadius: "md",
    colors: {
        sageBlue,
        sageSlate,
        sageGray,
    },
    other: {
        layoutTopbarHeight: 56,
        layoutRailCollapsed: 64,
        layoutRailExpanded: 220,
        layoutContextHeaderHeight: 48,
    },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
    variables: {
        "--sage-font-mono": FONT_MONO,
        /** Icon rail — light surface */
        "--sage-nav-bg": "#ffffff",
        "--sage-nav-bg-hover": "#f3f4f6",
        "--sage-nav-bg-active": "#eff6ff",
        "--sage-nav-text": "#6b7280",
        "--sage-nav-text-hover": "#111827",
        "--sage-nav-text-active": "#0090da",
        "--sage-nav-active-indicator": "#0090da",
        /** Global top bar */
        "--sage-topbar-bg": "#ffffff",
        "--sage-topbar-border": "#e5e7eb",
        /** Page */
        "--sage-page-bg": "#f9fafb",
        "--sage-surface-card": "#ffffff",
        "--sage-border-color": "#e5e7eb",
        "--sage-border-subtle": "#f3f4f6",
        "--sage-input-border": "#e5e7eb",
        "--sage-focus-ring": "#0090da",
        /** Brand */
        "--sage-brand-primary": "#0090da",
        "--sage-brand-primary-hover": "#0085cc",
        "--sage-brand-primary-subtle": "#e2faff",
        /** Semantic */
        "--sage-semantic-success": "#10b981",
        "--sage-semantic-warning": "#f59e0b",
        "--sage-semantic-error": "#ef4444",
        "--sage-semantic-info": "#3b82f6",
        /** Layout dimensions */
        "--sage-layout-topbar-height": "56px",
        "--sage-layout-nav-width": "64px",
        "--sage-layout-nav-width-expanded": "220px",
        "--sage-layout-context-header-height": "48px",
        /** Component */
        "--sage-button-radius": "8px",
        "--sage-card-radius": "12px",
    },
    light: {
        "--mantine-color-text": "#111827",
    },
    dark: {
        "--mantine-color-text": "#f1f5f9",
    },
});

export const lightShellPreset: SageThemePreset = {
    id: "light-shell",
    label: "Light Shell",
    description: "Icon Rail + Global Top Bar — Linear/Vercel 스타일",
    theme,
    cssVariablesResolver,
    figmaTokensPath: "figma/light-shell.tokens.json",
};
