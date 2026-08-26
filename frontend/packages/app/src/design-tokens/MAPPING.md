# Figma ↔ Mantine CSS Variables 매핑표

3방향 테마의 **Figma Variable → Mantine CSS Variable → Mantine Theme 속성** 전체 매핑입니다.

---

## ① Light Shell

### Color

| Figma Variable | CSS Variable | Hex | Mantine |
|----------------|--------------|-----|---------|
| `color/surface/page` | `--sage-page-bg` | `#F9FAFB` | — |
| `color/surface/rail` | `--sage-nav-bg` | `#FFFFFF` | — |
| `color/surface/rail-hover` | `--sage-nav-bg-hover` | `#F3F4F6` | `sageGray[1]` |
| `color/surface/rail-active` | `--sage-nav-bg-active` | `#EFF6FF` | — |
| `color/surface/header` | `--sage-topbar-bg` | `#FFFFFF` | — |
| `color/surface/card` | `--sage-surface-card` | `#FFFFFF` | — |
| `color/border/default` | `--sage-border-color` | `#E5E7EB` | `sageGray[2]` |
| `color/border/focus` | `--sage-focus-ring` | `#0090DA` | `sageBlue[7]` |
| `color/text/primary` | `--mantine-color-text` | `#111827` | light mode |
| `color/text/secondary` | — | `#6B7280` | `sageGray[5]` |
| `color/text/nav-active` | `--sage-nav-text-active` | `#0090DA` | `primaryColor` |
| `color/text/nav-default` | `--sage-nav-text` | `#6B7280` | — |
| `color/brand/primary` | `--sage-brand-primary` | `#0090DA` | `sageBlue[7]` |
| `color/brand/primary-hover` | `--sage-brand-primary-hover` | `#0085CC` | `sageBlue[8]` |
| `color/brand/primary-subtle` | `--sage-brand-primary-subtle` | `#E2FAFF` | `sageBlue[0]` |
| `color/semantic/success` | `--sage-semantic-success` | `#10B981` | — |
| `color/semantic/error` | `--sage-semantic-error` | `#EF4444` | — |
| `color/icon/active` | `--sage-nav-active-indicator` | `#0090DA` | rail left bar |

### Layout & Component

| Figma Variable | CSS Variable | Value |
|----------------|--------------|-------|
| `layout/topbar-height` | `--sage-layout-topbar-height` | `56px` |
| `layout/rail-width-collapsed` | `--sage-layout-nav-width` | `64px` |
| `layout/rail-width-expanded` | `--sage-layout-nav-width-expanded` | `220px` |
| `layout/context-header-height` | `--sage-layout-context-header-height` | `48px` |
| `radius/md` | `--sage-button-radius` | `8px` |
| `radius/lg` | `--sage-card-radius` | `12px` |
| `component/button-primary/height` | Mantine `Button` size | `36px` → `size="sm"` |
| `component/nav-rail-item/icon-size` | Tabler icon | `20px` |

### Mantine Theme Config

```ts
primaryColor: "sageBlue"
primaryShade: 7
defaultRadius: "md"
theme.other.layoutTopbarHeight: 56
```

---

## ② Command Center

### Color

| Figma Variable | CSS Variable | Hex | Mantine |
|----------------|--------------|-----|---------|
| `color/surface/topbar` | `--sage-topbar-bg` | `#18181B` | `sageZinc[9]` |
| `color/surface/topbar-hover` | `--sage-topbar-bg-hover` | `#27272A` | `sageZinc[8]` |
| `color/surface/nav` | `--sage-nav-bg` | `#FAFAFA` | `sageZinc[0]` |
| `color/surface/nav-hover` | `--sage-nav-bg-hover` | `#F4F4F5` | `sageZinc[1]` |
| `color/surface/nav-active` | `--sage-nav-bg-active` | `#F0FDFA` | `sageTeal[0]` |
| `color/surface/page` | `--sage-page-bg` | `#F4F4F5` | `sageZinc[1]` |
| `color/surface/panel` | `--sage-surface-panel` | `#FFFFFF` | — |
| `color/border/active` | `--sage-nav-active-indicator` | `#0D9488` | `sageTeal[6]` |
| `color/border/topbar` | `--sage-topbar-border` | `#27272A` | — |
| `color/text/topbar-primary` | `--sage-topbar-text` | `#FAFAFA` | — |
| `color/text/nav-active` | `--sage-nav-text-active` | `#0D9488` | `primaryColor` |
| `color/brand/primary` | `--sage-brand-primary` | `#0D9488` | `sageTeal[6]` |
| `color/brand/secondary` | `--sage-brand-secondary` | `#0090DA` | `sageBlue[7]` |
| `color/status/running` | `--sage-status-running` | `#22C55E` | Badge color |
| `color/category/data` | `--sage-category-data` | `#0D9488` | Nav icon |
| `color/category/report` | `--sage-category-report` | `#2563EB` | Nav icon |
| `color/category/tool` | `--sage-category-tool` | `#EA580C` | Nav icon |

### Layout & Component

| Figma Variable | CSS Variable | Value |
|----------------|--------------|-------|
| `layout/topbar-height` | `--sage-layout-topbar-height` | `48px` |
| `layout/nav-width` | `--sage-layout-nav-width` | `240px` |
| `layout/panel-left-width` | `--sage-layout-panel-left-width` | `280px` |
| `layout/panel-right-width` | `--sage-layout-panel-right-width` | `360px` |
| `radius/md` | `--sage-button-radius` | `6px` |
| `component/button-execute/height` | Execute button | `32px` → `size="compact-sm"` |
| `component/nav-leaf-item/active-border-width` | Nav active | `3px` left border |

### Mantine Theme Config

```ts
primaryColor: "sageTeal"
primaryShade: 6
defaultRadius: "sm"
theme.other.layoutTopbarHeight: 48
theme.other.layoutNavWidth: 240
```

---

## ③ Workspace Tabs

### Color

| Figma Variable | CSS Variable | Hex | Mantine |
|----------------|--------------|-----|---------|
| `color/surface/app-header` | `--sage-topbar-bg` | `#FFFFFF` | — |
| `color/surface/page` | `--sage-page-bg` | `#F0F4F8` | — |
| `color/surface/tab-active` | `--sage-surface-tab-active` | `#EFF6FF` | — |
| `color/surface/card` | `--sage-surface-card` | `#FFFFFF` | — |
| `color/surface/context-panel` | `--sage-surface-context-panel` | `#FFFFFF` | — |
| `color/border/tab-indicator` | `--sage-border-tab-indicator` | `#2563EB` | tab underline |
| `color/text/tab-active` | `--sage-nav-text-active` | `#2563EB` | `primaryColor` |
| `color/text/tab-default` | `--sage-nav-text` | `#64748B` | `sageSlate[5]` |
| `color/text/kpi-delta-up` | `--sage-kpi-delta-up` | `#059669` | — |
| `color/brand/primary` | `--sage-brand-primary` | `#2563EB` | `sageIndigo[7]` |
| `color/chart/series-1` | `--sage-chart-series-1` | `#2563EB` | Recharts |
| `color/chart/series-2` | `--sage-chart-series-2` | `#7C3AED` | Recharts |

### Layout & Component

| Figma Variable | CSS Variable | Value |
|----------------|--------------|-------|
| `layout/app-header-height` | `--sage-layout-topbar-height` | `52px` |
| `layout/page-toolbar-height` | `--sage-layout-toolbar-height` | `52px` |
| `layout/context-panel-width` | `--sage-layout-context-panel-width` | `320px` |
| `layout/grid-gutter` | `--sage-layout-grid-gutter` | `24px` |
| `radius/md` | `--sage-button-radius` | `10px` |
| `component/fab/size` | `--sage-fab-size` | `56px` |
| `component/tab-item/indicator-height` | Tab underline | `2px` |

### Mantine Theme Config

```ts
primaryColor: "sageIndigo"
primaryShade: 7
defaultRadius: "md"
theme.other.layoutAppHeaderHeight: 52
theme.other.layoutContextPanelWidth: 320
```

---

## App.tsx 적용 예시

```tsx
import {MantineProvider} from "@mantine/core";
import {getThemePreset} from "@/design-tokens/mantine";

// 환경변수 또는 설정으로 프리셋 선택
const THEME_ID = (import.meta.env.VITE_SAGE_THEME ?? "command-center") as SageThemePresetId;
const preset = getThemePreset(THEME_ID);

export function App() {
    return (
        <MantineProvider
            theme={preset.theme}
            cssVariablesResolver={preset.cssVariablesResolver}
        >
            {/* ... */}
        </MantineProvider>
    );
}
```

## 기존 Theme.ts와의 관계

| 파일 | 역할 |
|------|------|
| `src/libs/Theme.ts` | **현재 운영 테마** (Premium Slate, `#0F172A` sidebar) |
| `src/design-tokens/mantine/theme*.ts` | **신규 3방향 프리셋** (레이아웃 재구성용) |

마이그레이션 시 `Theme.ts`를 선택한 프리셋으로 교체하거나, `Theme.ts`에서 `getThemePreset()`을 re-export하면 됩니다.

## Figma Import 빠른 참조

| 방향 | JSON 파일 | Figma Collection |
|------|-----------|------------------|
| ① | `figma/light-shell.tokens.json` | SAG-E / Light Shell |
| ② | `figma/command-center.tokens.json` | SAG-E / Command Center |
| ③ | `figma/workspace-tabs.tokens.json` | SAG-E / Workspace Tabs |
