import {useState} from "react";
import {
    IconBell,
    IconChartBar,
    IconDatabase,
    IconFileAnalytics,
    IconList,
    IconTool,
    IconUser,
} from "@tabler/icons-react";
import {getPresetStyleVars} from "../previewTokens";
import MockMainContent from "../MockMainContent";
import classes from "../layoutPreview.module.css";

const RAIL_ITEMS = [
    {label: "대시보드", icon: IconChartBar, active: true},
    {label: "데이터 분석 모델", icon: IconDatabase, section: "데이터"},
    {label: "보고서", icon: IconFileAnalytics, section: "데이터"},
    {label: "보고서 목록", icon: IconList, section: "데이터"},
    {label: "도구(Tool)", icon: IconTool, section: "설정"},
];

export default function LightShellPreview() {
    const [railExpanded, setRailExpanded] = useState(false);
    const style = getPresetStyleVars("light-shell");

    return (
        <div className={classes.previewFrame} style={style}>
            {/* Top: 브랜드 + 유틸리티만 (내비 중복 없음) */}
            <header className={classes.lightTopBar}>
                <div className={classes.lightTopBrand}>
                    <IconDatabase size={20} color="var(--sage-brand-primary)"/>
                    SAG-E
                </div>
                <div className={classes.lightTopSpacer}/>
                <input className={classes.lightSearch} readOnly placeholder="모델, 보고서 검색..." />
                <IconBell size={20} color="#6b7280"/>
                <IconUser size={20} color="#6b7280"/>
            </header>

            <div className={classes.shellBody}>
                {/* Left: 유일한 글로벌 내비게이션 */}
                <aside
                    className={classes.lightRail}
                    data-expanded={railExpanded || undefined}
                    onMouseEnter={() => setRailExpanded(true)}
                    onMouseLeave={() => setRailExpanded(false)}
                >
                    {RAIL_ITEMS.map(({label, icon: Icon, active}) => (
                        <div
                            key={label}
                            className={classes.railItem}
                            data-active={active || undefined}
                        >
                            <Icon size={20} stroke={active ? 2 : 1.75}/>
                            {railExpanded && <span className={classes.railLabel}>{label}</span>}
                        </div>
                    ))}
                </aside>

                <div className={classes.shellMain}>
                    <div className={classes.contextHeader}>
                        <span className={classes.contextTitle}>대시보드</span>
                        <div className={classes.contextActions}>
                            <button type="button" className={classes.btnSecondary}>내보내기</button>
                            <button type="button" className={classes.btnPrimary}>새로고침</button>
                        </div>
                    </div>
                    <div className={classes.mainScroll}>
                        <MockMainContent primaryColor="var(--sage-brand-primary)"/>
                    </div>
                </div>
            </div>
        </div>
    );
}
