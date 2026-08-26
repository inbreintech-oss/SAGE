import {createTheme, type CSSVariablesResolver} from "@mantine/core";
import type {SageThemePreset} from "./types";
import {FONT_FAMILY, FONT_MONO, sageBlue, sageIndigo, sageSlate} from "./sharedColors";

const theme = createTheme({
    fontFamily: FONT_FAMILY,
    fontFamilyMonospace: FONT_MONO,
    primaryColor: "sageIndigo",
    primaryShade: 7,
    defaultRadius: "md",
    colors: {
        sageIndigo,
        sageBlue,
        sageSlate,
    },
    other: {
        layoutAppHeaderHeight: 52,
        layoutPageToolbarHeight: 52,
        layoutContextPanelWidth: 320,
        gridColumns: 12,
        gridGutter: 24,
    },
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
    variables: {
        "--sage-font-mono": FONT_MONO,
        /** Top tab navigation — no left sidebar */
        "--sage-nav-bg": "#ffffff",
        "--sage-nav-bg-hover": "#f8fafc",
        "--sage-nav-bg-active": "#eff6ff",
        "--sage-nav-text": "#64748b",
        "--sage-nav-text-hover": "#0f172a",
        "--sage-nav-text-active": "#2563eb",
        "--sage-nav-active-indicator": "#2563eb",
        /** App header & toolbar */
        "--sage-topbar-bg": "#ffffff",
        "--sage-topbar-border": "#e2e8f0",
        "--sage-toolbar-bg": "#ffffff",
        /** Page */
        "--sage-page-bg": "#f0f4f8",
        "--sage-surface-card": "#ffffff",
        "--sage-surface-tab-active": "#eff6ff",
        "--sage-surface-context-panel": "#ffffff",
        "--sage-border-color": "#e2e8f0",
        "--sage-border-tab-indicator": "#2563eb",
        "--sage-input-border": "#e2e8f0",
        "--sage-focus-ring": "#2563eb",
        /** Brand */
        "--sage-brand-primary": "#2563eb",
        "--sage-brand-primary-hover": "#1d4ed8",
        "--sage-brand-secondary": "#0090da",
        "--sage-brand-accent-purple": "#7c3aed",
        "--sage-brand-accent-cyan": "#06b6d4",
        /** Chart series */
        "--sage-chart-series-1": "#2563eb",
        "--sage-chart-series-2": "#7c3aed",
        "--sage-chart-series-3": "#06b6d4",
        "--sage-chart-series-4": "#f59e0b",
        /** KPI */
        "--sage-kpi-delta-up": "#059669",
        "--sage-kpi-delta-down": "#dc2626",
        /** Layout dimensions */
        "--sage-layout-topbar-height": "52px",
        "--sage-layout-toolbar-height": "52px",
        "--sage-layout-context-panel-width": "320px",
        "--sage-layout-grid-gutter": "24px",
        "--sage-layout-grid-margin": "32px",
        /** Component */
        "--sage-button-radius": "10px",
        "--sage-card-radius": "12px",
        "--sage-fab-size": "56px",
    },
    light: {
        "--mantine-color-text": "#0f172a",
    },
    dark: {
        "--mantine-color-text": "#f1f5f9",
    },
});

export const workspaceTabsPreset: SageThemePreset = {
    id: "workspace-tabs",
    label: "Workspace Tabs",
    description: "Top Tab Navigation + Context Panel — Power BI/Looker 스타일",
    theme,
    cssVariablesResolver,
    figmaTokensPath: "figma/workspace-tabs.tokens.json",
};
