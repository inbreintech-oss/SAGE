# SAG-E Design Tokens

3가지 레이아웃 방향(Light Shell, Command Center, Workspace Tabs)의 디자인 토큰 정의입니다.

## 디렉터리

```
src/design-tokens/
├── README.md                          ← 이 파일 (매핑 가이드)
├── MAPPING.md                         ← Figma ↔ CSS ↔ Mantine 전체 매핑표
├── figma/
│   ├── light-shell.tokens.json        ← ① Light Shell (Tokens Studio / Figma Variables)
│   ├── command-center.tokens.json     ← ② Command Center
│   └── workspace-tabs.tokens.json     ← ③ Workspace Tabs
└── mantine/
    ├── types.ts                       ← 공통 타입
    ├── themeLightShell.ts             ← Mantine 테마 프리셋 ①
    ├── themeCommandCenter.ts          ← Mantine 테마 프리셋 ②
    ├── themeWorkspaceTabs.ts          ← Mantine 테마 프리셋 ③
    └── index.ts                       ← 프리셋 선택 헬퍼
```

## Figma Variables 등록 방법

### 방법 A — Tokens Studio 플러그인 (권장)

1. Figma → Plugins → **Tokens Studio for Figma** 실행
2. **Import** → `design-tokens/figma/{theme}.tokens.json` 선택
3. **Styles & Variables** → **Create variables** 로 Figma Variables 동기화
4. Collection 이름: `SAG-E / Light Shell` (파일 내 `$metadata.collection` 참고)

### 브라우저 미리보기 (개발 서버)

```
http://localhost:5000/layout-preview
```

- **단일 보기**: 3방향 중 하나를 전체 화면으로 확인
- **4종 비교**: ①②③④ 레이아웃 2×2 그리드
- **Light/Dark**: ④ 권장안 Light/Dark 모드 나란히 비교 (Light Top + Adaptive Rail/Main)
- ④ 단일 보기: **☀ Light / ☾ Dark** 토글로 Rail·Main·Card 색상 전환 확인

### 방법 B — 수동 등록

각 JSON의 `$value`를 Figma Variables에 아래 네이밍으로 등록합니다.

| JSON 경로 | Figma Variable Name |
|-----------|---------------------|
| `color.surface.page` | `color/surface/page` |
| `color.brand.primary` | `color/brand/primary` |
| `spacing.4` | `spacing/4` |
| `radius.md` | `radius/md` |

## Mantine 테마 적용 방법

`App.tsx`에서 프리셋을 교체합니다.

```tsx
import { getThemePreset } from "@/design-tokens/mantine";

const preset = getThemePreset("command-center"); // "light-shell" | "command-center" | "workspace-tabs"

<MantineProvider theme={preset.theme} cssVariablesResolver={preset.cssVariablesResolver}>
```

## CSS 변수 ↔ Figma Variable 매핑표

### 공통 토큰

| Figma Variable | CSS Variable (`--sage-*`) | 용도 |
|----------------|---------------------------|------|
| `color/surface/page` | `--sage-page-bg` | 본문 배경 |
| `color/surface/nav` | `--sage-nav-bg` | 내비 배경 |
| `color/surface/nav-hover` | `--sage-nav-bg-hover` | 내비 호버 |
| `color/surface/nav-active` | `--sage-nav-bg-active` | 내비 활성 |
| `color/text/nav` | `--sage-nav-text` | 내비 텍스트 |
| `color/text/nav-hover` | `--sage-nav-text-hover` | 내비 호버 텍스트 |
| `color/text/nav-active` | `--sage-nav-text-active` | 내비 활성 텍스트 |
| `color/border/default` | `--sage-border-color` | 경계선 |
| `color/border/input` | `--sage-input-border` | 인풋 테두리 |
| `color/brand/primary` | `--sage-focus-ring` | 포커스 링 |
| `color/brand/primary` | `--sage-nav-bg-active` (일부 테마) | Primary CTA |

### 방향별 Primary Color

| 방향 | Primary | Mantine `primaryColor` |
|------|---------|------------------------|
| **④ 권장안** | `#0D9488` (Teal) | `sageTeal` — ②+①+③ 하이브리드 |
| ① Light Shell | `#0090DA` | `sageBlue` |
| ② Command Center | `#0D9488` | `sageTeal` |
| ③ Workspace Tabs | `#2563EB` | `sageIndigo` |

### 레이아웃 치수 (Figma Frame ↔ CSS)

| Token | Light Shell | Command Center | Workspace Tabs |
|-------|-------------|----------------|----------------|
| `layout/topbar-height` | 56px | 48px | 52px |
| `layout/nav-width` | 64px (220px expanded) | 240px | — (탭 내비) |
| `layout/context-header-height` | 48px | 44px | 52px |
| `layout/context-panel-width` | — | — | 320px |

## Typography (3방향 공통)

| Figma Text Style | Size | Weight | Line | CSS |
|------------------|------|--------|------|-----|
| `Text/H1` | 24–28px | 700 | 32–36px | `--mantine-h1-*` |
| `Text/H2` | 18–20px | 600 | 26–28px | `--mantine-h2-*` |
| `Text/Body/M` | 14px | 400 | 22px | body default |
| `Text/Label/M` | 12px | 500 | 16px | form labels |
| `Text/Nav/Section` | 11px | 600 | 14px | UPPERCASE section |

Font Family: **Noto Sans KR** (`theme.fontFamily`)  
Mono: **Fira Code** (`--sage-font-mono`)
