import {useState, type ReactNode} from "react";
import {Badge, Button, Group, SegmentedControl, Stack, Text} from "@mantine/core";
import {Link} from "react-router-dom";
import {IconLayoutGrid, IconLayoutNavbar, IconLayoutSidebar} from "@tabler/icons-react";
import type {SageThemePresetId} from "@/design-tokens/mantine";
import {SAGE_THEME_PRESETS} from "@/design-tokens/mantine";
import LightShellPreview from "./shells/LightShellPreview";
import CommandCenterPreview from "./shells/CommandCenterPreview";
import WorkspaceTabsPreview, {WorkspaceTabsDetailPreview} from "./shells/WorkspaceTabsPreview";
import RecommendedPreview, {
    RecommendedThemeCompare,
    type RecommendedNavMode,
    type RecommendedScene,
} from "./shells/RecommendedPreview";
import type {PreviewColorScheme} from "./previewTokens";
import classes from "./layoutPreview.module.css";

type ViewMode = "single" | "layouts" | "theme";

const PRESET_OPTIONS: {value: SageThemePresetId; label: string}[] = [
    {value: "recommended", label: "④ 권장안"},
    {value: "light-shell", label: "① Light Shell"},
    {value: "command-center", label: "② Command Center"},
    {value: "workspace-tabs", label: "③ Workspace Tabs"},
];

const SHELLS: Record<SageThemePresetId, () => ReactNode> = {
    recommended: () => <RecommendedPreview scene="dashboard" navMode="rail" colorScheme="light"/>,
    "light-shell": () => <LightShellPreview/>,
    "command-center": () => <CommandCenterPreview/>,
    "workspace-tabs": () => <WorkspaceTabsPreview/>,
};

export default function LayoutPreviewPage() {
    const [presetId, setPresetId] = useState<SageThemePresetId>("recommended");
    const [viewMode, setViewMode] = useState<ViewMode>("single");
    const [workspaceScene, setWorkspaceScene] = useState<"home" | "detail">("home");
    const [recommendedScene, setRecommendedScene] = useState<RecommendedScene>("dashboard");
    const [recommendedNavMode, setRecommendedNavMode] = useState<RecommendedNavMode>("rail");
    const [colorScheme, setColorScheme] = useState<PreviewColorScheme>("light");

    const preset = SAGE_THEME_PRESETS[presetId];

    const renderShell = (id: SageThemePresetId) => {
        if (id === "workspace-tabs" && workspaceScene === "detail") {
            return <WorkspaceTabsDetailPreview/>;
        }
        if (id === "recommended") {
            return (
                <RecommendedPreview
                    scene={recommendedScene}
                    navMode={recommendedNavMode}
                    colorScheme={colorScheme}
                />
            );
        }
        return SHELLS[id]();
    };

    return (
        <div className={classes.previewPage}>
            <header className={classes.previewChrome}>
                <Stack gap={2}>
                    <Group gap="sm">
                        <Text className={classes.previewChromeTitle}>레이아웃 미리보기</Text>
                        {presetId === "recommended" && (
                            <Badge size="sm" color="teal" variant="light">권장</Badge>
                        )}
                    </Group>
                    <Text className={classes.previewChromeDesc}>
                        {preset.description} · Noto Sans KR · design-tokens 기반
                    </Text>
                </Stack>

                <Group gap="md" wrap="wrap" justify="flex-end">
                    <SegmentedControl
                        value={viewMode}
                        onChange={(v) => setViewMode(v as ViewMode)}
                        data={[
                            {label: "단일", value: "single"},
                            {label: "4종 비교", value: "layouts"},
                            {label: "Light/Dark", value: "theme"},
                        ]}
                        size="xs"
                    />

                    {viewMode === "single" && presetId === "recommended" && (
                        <SegmentedControl
                            value={colorScheme}
                            onChange={(v) => setColorScheme(v as PreviewColorScheme)}
                            data={[
                                {label: "☀ Light", value: "light"},
                                {label: "☾ Dark", value: "dark"},
                            ]}
                            size="xs"
                        />
                    )}

                    {viewMode === "single" && presetId === "recommended" && (
                        <SegmentedControl
                            value={recommendedNavMode}
                            onChange={(v) => setRecommendedNavMode(v as RecommendedNavMode)}
                            data={[
                                {label: "Icon Rail", value: "rail"},
                                {label: "Sidebar", value: "sidebar"},
                            ]}
                            size="xs"
                        />
                    )}

                    {(viewMode === "single" || viewMode === "theme") && presetId === "recommended" && (
                        <SegmentedControl
                            value={recommendedScene}
                            onChange={(v) => setRecommendedScene(v as RecommendedScene)}
                            data={[
                                {label: "대시보드", value: "dashboard"},
                                {label: "작업(3패널)", value: "workspace"},
                            ]}
                            size="xs"
                        />
                    )}

                    {viewMode === "single" && presetId === "workspace-tabs" && (
                        <SegmentedControl
                            value={workspaceScene}
                            onChange={(v) => setWorkspaceScene(v as "home" | "detail")}
                            data={[
                                {label: "홈", value: "home"},
                                {label: "상세", value: "detail"},
                            ]}
                            size="xs"
                        />
                    )}

                    {viewMode === "single" && (
                        <SegmentedControl
                            value={presetId}
                            onChange={(v) => setPresetId(v as SageThemePresetId)}
                            data={PRESET_OPTIONS}
                            size="xs"
                        />
                    )}

                    <Button component={Link} to="/" variant="light" size="xs">
                        앱으로 돌아가기
                    </Button>
                </Group>
            </header>

            <div className={classes.previewFrameWrap}>
                {viewMode === "layouts" && (
                    <div className={classes.compareGrid}>
                        {PRESET_OPTIONS.map(({value, label}) => (
                            <div key={value} className={classes.compareCell}>
                                <div className={classes.compareLabel}>{label}</div>
                                <div className={classes.compareFrame}>
                                    {value === "recommended"
                                        ? (
                                            <RecommendedPreview
                                                scene="dashboard"
                                                navMode="rail"
                                                colorScheme="light"
                                                compact
                                            />
                                        )
                                        : SHELLS[value]()}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {viewMode === "theme" && (
                    <RecommendedThemeCompare
                        scene={recommendedScene}
                        navMode={recommendedNavMode}
                    />
                )}

                {viewMode === "single" && renderShell(presetId)}
            </div>

            {viewMode === "single" && (
                <Group justify="center" pb="md" gap="lg">
                    <Group gap={6}>
                        <IconLayoutNavbar size={14} color="#64748b"/>
                        <Text size="xs" c="dimmed">Top: Light · {preset.theme.other?.layoutTopbarHeight ?? 48}px</Text>
                    </Group>
                    <Group gap={6}>
                        <IconLayoutSidebar size={14} color="#64748b"/>
                        <Text size="xs" c="dimmed">
                            Nav: {String(preset.theme.other?.layoutNavWidth ?? "Rail")}
                        </Text>
                    </Group>
                    <Group gap={6}>
                        <IconLayoutGrid size={14} color="#64748b"/>
                        <Text size="xs" c="dimmed">Primary: {preset.theme.primaryColor}</Text>
                    </Group>
                    {presetId === "recommended" && (
                        <Text size="xs" c="dimmed">
                            Top: {colorScheme === "light" ? "#FFFFFF" : "#27272A"}
                        </Text>
                    )}
                </Group>
            )}

            {viewMode === "theme" && (
                <Group justify="center" pb="md" gap="lg">
                    <Text size="xs" c="dimmed">
                        Light: Top #FFF · Dark: Top #27272A — Rail/Main은 Light↔Dark
                    </Text>
                </Group>
            )}
        </div>
    );
}
