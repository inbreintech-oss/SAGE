import {
    IconBell,
    IconChartBar,
    IconChevronDown,
    IconDatabase,
    IconFileAnalytics,
    IconList,
    IconTool,
    IconUser,
} from "@tabler/icons-react";
import {getPresetStyleVars} from "../previewTokens";
import MockMainContent, {ExecuteButton} from "../MockMainContent";
import classes from "../layoutPreview.module.css";

const NAV_SECTIONS = [
    {
        title: "데이터",
        items: [
            {label: "데이터 분석 모델", icon: IconDatabase, active: true, color: "var(--sage-category-data)"},
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

export default function CommandCenterPreview() {
    const style = getPresetStyleVars("command-center");

    return (
        <div className={classes.previewFrame} style={style}>
            <header className={classes.commandTopBar}>
                <div className={classes.commandTopLeft}>
                    <IconDatabase size={18} color="#fafafa"/>
                    <span className={classes.commandBrand}>SAG-E</span>
                    <div className={classes.commandWorkspace}>
                        Production <IconChevronDown size={14}/>
                    </div>
                </div>
                <div className={classes.commandTopRight}>
                    <span><span className={classes.statusDot}/>실행중 3</span>
                    <IconBell size={18}/>
                    <IconUser size={18}/>
                    admin
                </div>
            </header>

            <div className={classes.shellBody}>
                <nav className={classes.commandNav}>
                    <div
                        className={classes.navLeaf}
                        data-active={undefined}
                        style={{marginTop: 4, fontWeight: 500}}
                    >
                        <IconChartBar size={18} color="var(--sage-category-dashboard)"/>
                        대시보드
                    </div>
                    {NAV_SECTIONS.map((section) => (
                        <div key={section.title}>
                            <div className={classes.navSection}>{section.title}</div>
                            {section.items.map(({label, icon: Icon, active, color}) => (
                                <div
                                    key={label}
                                    className={classes.navLeaf}
                                    data-active={active || undefined}
                                >
                                    <Icon size={18} color={active ? "var(--sage-nav-text-active)" : color}/>
                                    {label}
                                </div>
                            ))}
                        </div>
                    ))}
                </nav>

                <div className={classes.shellMain}>
                    <div className={classes.contextHeader}>
                        <span className={classes.contextTitle}>데이터 분석 모델</span>
                        <div className={classes.contextActions}>
                            <ExecuteButton color="var(--sage-brand-primary)"/>
                            <button type="button" className={classes.btnSecondary}>저장</button>
                        </div>
                    </div>
                    <div className={classes.mainScroll} style={{padding: 0}}>
                        <MockMainContent variant="workspace" primaryColor="var(--sage-brand-primary)"/>
                    </div>
                </div>
            </div>
        </div>
    );
}
