import {useState} from "react";
import {
    IconBell,
    IconChartBar,
    IconChevronDown,
    IconDatabase,
    IconFileAnalytics,
    IconList,
    IconSearch,
    IconTool,
    IconTrendingUp,
    IconUser,
} from "@tabler/icons-react";
import type {TablerIcon} from "@tabler/icons-react";
import {getPresetStyleVars, type PreviewColorScheme} from "../previewTokens";
import MockMainContent, {ExecuteButton} from "../MockMainContent";
import classes from "../layoutPreview.module.css";

export type RecommendedScene = "dashboard" | "workspace";
export type RecommendedNavMode = "sidebar" | "rail";

type RecommendedPreviewProps = Readonly<{
    scene?: RecommendedScene;
    navMode?: RecommendedNavMode;
    colorScheme?: PreviewColorScheme;
    compact?: boolean;
}>;

const NAV_SECTIONS = [
    {
        title: "데이터",
        items: [
            {label: "데이터 분석 모델", icon: IconDatabase, color: "var(--sage-category-data)"},
            {label: "보고서", icon: IconFileAnalytics, color: "var(--sage-category-report)"},
            {label: "보고서 목록", icon: IconList, color: "var(--sage-category-report)"},
        ],
    },
    {
        title: "핵심 자산 설정",
        items: [
            {label: "도구(Tool)", icon: IconTool, color: "var(--sage-category-tool)"},
        ],
    },
];

type NavItem = {
    label: string;
    icon: TablerIcon;
    color?: string;
    section?: string;
};

const NAV_ITEMS: NavItem[] = [
    {label: "대시보드", icon: IconChartBar, color: "var(--sage-category-dashboard)"},
    {label: "데이터 분석 모델", icon: IconDatabase, color: "var(--sage-category-data)", section: "데이터"},
    {label: "보고서", icon: IconFileAnalytics, color: "var(--sage-category-report)", section: "데이터"},
    {label: "보고서 목록", icon: IconList, color: "var(--sage-category-report)", section: "데이터"},
    {label: "도구(Tool)", icon: IconTool, color: "var(--sage-category-tool)", section: "핵심 자산 설정"},
];

function isItemActive(label: string, isDashboard: boolean) {
    if (isDashboard) return label === "대시보드";
    return label === "데이터 분석 모델";
}

function SidebarNav({isDashboard}: Readonly<{isDashboard: boolean}>) {
    return (
        <nav className={classes.commandNav}>
            {NAV_ITEMS.map(({label, icon: Icon, color}) => {
                if (label === "대시보드") {
                    const active = isItemActive(label, isDashboard);
                    return (
                        <div
                            key={label}
                            className={classes.navLeaf}
                            data-active={active || undefined}
                            style={{marginTop: 4, fontWeight: active ? 600 : 500}}
                        >
                            <Icon size={18} color={active ? "var(--sage-nav-text-active)" : color}/>
                            {label}
                        </div>
                    );
                }
                return null;
            })}
            {NAV_SECTIONS.map((section) => (
                <div key={section.title}>
                    <div className={classes.navSection}>{section.title}</div>
                    {section.items.map(({label, icon: Icon, color}) => {
                        const active = isItemActive(label, isDashboard);
                        return (
                            <div key={label} className={classes.navLeaf} data-active={active || undefined}>
                                <Icon size={18} color={active ? "var(--sage-nav-text-active)" : color}/>
                                {label}
                            </div>
                        );
                    })}
                </div>
            ))}
        </nav>
    );
}

function RailNav({isDashboard}: Readonly<{isDashboard: boolean}>) {
    const [expanded, setExpanded] = useState(false);

    let lastSection = "";

    return (
        <nav
            className={classes.recommendedRail}
            data-expanded={expanded || undefined}
            onMouseEnter={() => setExpanded(true)}
            onMouseLeave={() => setExpanded(false)}
        >
            {NAV_ITEMS.map(({label, icon: Icon, color, section}) => {
                const active = isItemActive(label, isDashboard);
                const showSection = expanded && section && section !== lastSection;
                if (showSection) lastSection = section;

                return (
                    <div key={label}>
                        {showSection && (
                            <div className={classes.railSectionLabel}>{section}</div>
                        )}
                        <div
                            className={classes.railItem}
                            data-active={active || undefined}
                            title={!expanded ? label : undefined}
                        >
                            <Icon size={20} stroke={active ? 2.25 : 1.75} color={active ? "var(--sage-nav-text-active)" : color}/>
                            {expanded && <span className={classes.railLabel}>{label}</span>}
                        </div>
                    </div>
                );
            })}
        </nav>
    );
}

function DashboardKpiContent() {
    return (
        <div className={classes.recommendedDashboard}>
            <div className={classes.recommendedKpiRow}>
                {[
                    {label: "등록 모델", value: "24", delta: "+3", up: true},
                    {label: "보고서", value: "156", delta: "+12", up: true},
                    {label: "실행 중", value: "3", delta: "Live", up: true},
                    {label: "완료율", value: "94%", delta: "+2%", up: true},
                ].map((kpi) => (
                    <div key={kpi.label} className={classes.recommendedKpiCard}>
                        <span className={classes.recommendedKpiLabel}>{kpi.label}</span>
                        <span className={classes.recommendedKpiValue}>{kpi.value}</span>
                        <span
                            className={classes.recommendedKpiDelta}
                            style={{color: kpi.up ? "var(--sage-kpi-delta-up)" : "var(--sage-kpi-delta-down)"}}
                        >
                            {kpi.delta}
                        </span>
                    </div>
                ))}
            </div>
            <div className={classes.recommendedChartRow}>
                <div className={classes.recommendedChartCard}>
                    <div className={classes.chartCardHeader}>
                        <span>월별 보고서 생성 추이</span>
                        <IconTrendingUp size={16} color="var(--sage-brand-primary)"/>
                    </div>
                    <div className={classes.chartBars}>
                        {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                            <div
                                key={i}
                                className={classes.chartBar}
                                style={{
                                    height: `${h}%`,
                                    backgroundColor: [
                                        "var(--sage-chart-series-1)",
                                        "var(--sage-chart-series-2)",
                                        "var(--sage-chart-series-3)",
                                        "var(--sage-chart-series-4)",
                                    ][i % 4],
                                    opacity: 0.85,
                                }}
                            />
                        ))}
                    </div>
                </div>
                <div className={classes.recommendedRecentCard}>
                    <div className={classes.chartCardHeader}>
                        <span>최근 보고서</span>
                        <IconFileAnalytics size={16} color="var(--sage-brand-secondary)"/>
                    </div>
                    {["2026 Q1 매출 리포트", "고객 이탈 분석", "재고 최적화 보고서", "월간 KPI 요약"].map((title) => (
                        <div key={title} className={classes.recentRow}>{title}</div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default function RecommendedPreview({
    scene = "dashboard",
    navMode = "rail",
    colorScheme = "light",
    compact = false,
}: RecommendedPreviewProps) {
    const style = getPresetStyleVars("recommended", colorScheme);
    const isDashboard = scene === "dashboard";

    return (
        <div
            className={compact ? `${classes.previewFrame} ${classes.previewFrameCompact}` : classes.previewFrame}
            style={style}
            data-mantine-color-scheme={colorScheme}
        >
            {/* Light Top — 검색 · 상태 · 유틸리티 */}
            <header className={classes.recommendedTopBar}>
                <div className={classes.commandTopLeft}>
                    <IconDatabase size={18} color="var(--sage-brand-primary)"/>
                    <span className={classes.commandBrand}>SAG-E</span>
                    <div className={classes.commandWorkspace}>
                        Production <IconChevronDown size={14}/>
                    </div>
                </div>
                <div className={classes.commandTopSearchWrap}>
                    <IconSearch size={16} color="var(--sage-topbar-icon, #71717a)"/>
                    <input
                        className={classes.commandTopSearch}
                        readOnly
                        placeholder="모델, 보고서, 도구 검색..."
                    />
                </div>
                <div className={classes.commandTopRight}>
                    <span><span className={classes.statusDot}/>실행중 3</span>
                    <IconBell size={18} color="var(--sage-topbar-icon, #71717a)"/>
                    <IconUser size={18} color="var(--sage-topbar-icon, #71717a)"/>
                    admin
                </div>
            </header>

            <div className={classes.shellBody}>
                {navMode === "rail" ? (
                    <RailNav isDashboard={isDashboard}/>
                ) : (
                    <SidebarNav isDashboard={isDashboard}/>
                )}

                <div
                    className={classes.shellMain}
                    style={isDashboard ? {background: "var(--sage-page-bg-dashboard)"} : undefined}
                >
                    <div className={classes.contextHeader}>
                        <span className={classes.contextTitle}>
                            {isDashboard ? "대시보드" : "데이터 분석 모델"}
                        </span>
                        <div className={classes.contextActions}>
                            {isDashboard ? (
                                <>
                                    <button type="button" className={classes.btnSecondary}>내보내기</button>
                                    <button type="button" className={classes.btnPrimary}>새로고침</button>
                                </>
                            ) : (
                                <>
                                    <ExecuteButton color="var(--sage-brand-primary)"/>
                                    <button type="button" className={classes.btnSecondary}>저장</button>
                                </>
                            )}
                        </div>
                    </div>
                    <div className={classes.mainScroll} style={isDashboard ? undefined : {padding: 0}}>
                        {isDashboard ? (
                            <DashboardKpiContent/>
                        ) : (
                            <MockMainContent variant="workspace" primaryColor="var(--sage-brand-primary)"/>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

/** Light / Dark 모드 나란히 비교 */
export function RecommendedThemeCompare({
    scene = "dashboard",
    navMode = "rail",
}: Readonly<{
    scene?: RecommendedScene;
    navMode?: RecommendedNavMode;
}>) {
    return (
        <div className={classes.themeCompareGrid}>
            <div className={classes.themeCompareCell}>
                <div className={classes.compareLabel}>
                    Light Mode · Light Top · Rail/Main 밝음
                </div>
                <RecommendedPreview
                    scene={scene}
                    navMode={navMode}
                    colorScheme="light"
                    compact
                />
            </div>
            <div className={classes.themeCompareCell}>
                <div className={classes.compareLabel}>
                    Dark Mode · Top #27272A · Rail/Main 어두움
                </div>
                <RecommendedPreview
                    scene={scene}
                    navMode={navMode}
                    colorScheme="dark"
                    compact
                />
            </div>
        </div>
    );
}
