import {IconFilePlus, IconSettings, IconUser} from "@tabler/icons-react";
import {getPresetStyleVars, PREVIEW_TABS} from "../previewTokens";
import MockMainContent from "../MockMainContent";
import classes from "../layoutPreview.module.css";

export default function WorkspaceTabsPreview() {
    const style = getPresetStyleVars("workspace-tabs");

    return (
        <div className={classes.previewFrame} style={style}>
            {/* Top: 유일한 글로벌 내비게이션 (탭) */}
            <header className={classes.tabsHeader}>
                <div className={classes.tabsBrand}>SAG-E</div>
                <nav className={classes.tabsList}>
                    {PREVIEW_TABS.map((tab) => (
                        <span
                            key={tab}
                            className={classes.tabItem}
                            data-active={tab === "홈" || undefined}
                        >
                            {tab}
                        </span>
                    ))}
                </nav>
                <IconSettings size={20} color="#64748b"/>
                <IconUser size={20} color="#64748b" style={{marginLeft: 12}}/>
            </header>

            <div className={classes.pageToolbar}>
                <span className={classes.breadcrumb}>
                    홈 / <strong>대시보드</strong>
                </span>
                <div className={classes.contextActions}>
                    <button type="button" className={classes.btnSecondary}>미리보기</button>
                    <button type="button" className={classes.btnPrimary}>배포</button>
                </div>
            </div>

            {/* 홈(대시보드): 좌측 패널 없음 — Top 탭만으로 충분 */}
            <div className={classes.tabsBody}>
                <div className={classes.tabsMain} style={{width: "100%"}}>
                    <div className={classes.mainScroll}>
                        <MockMainContent primaryColor="var(--sage-brand-primary)"/>
                    </div>
                </div>
            </div>
        </div>
    );
}

/** 상세/편집 페이지용 — 좌측 컨텍스트 패널은 이때만 등장 */
export function WorkspaceTabsDetailPreview() {
    const style = getPresetStyleVars("workspace-tabs");

    return (
        <div className={classes.previewFrame} style={style}>
            <header className={classes.tabsHeader}>
                <div className={classes.tabsBrand}>SAG-E</div>
                <nav className={classes.tabsList}>
                    {PREVIEW_TABS.map((tab) => (
                        <span
                            key={tab}
                            className={classes.tabItem}
                            data-active={tab === "보고서" || undefined}
                        >
                            {tab}
                        </span>
                    ))}
                </nav>
                <IconSettings size={20} color="#64748b"/>
                <IconUser size={20} color="#64748b" style={{marginLeft: 12}}/>
            </header>

            <div className={classes.pageToolbar}>
                <span className={classes.breadcrumb}>
                    보고서 / <strong>월간 매출 리포트</strong>
                </span>
                <div className={classes.contextActions}>
                    <button type="button" className={classes.btnSecondary}>미리보기</button>
                    <button type="button" className={classes.btnPrimary}>배포</button>
                </div>
            </div>

            <div className={classes.tabsBody}>
                {/* Left: 내비가 아닌 컨텍스트(목록/필터) — Top 탭과 역할 분리 */}
                <aside className={classes.contextPanel}>
                    <div className={classes.contextPanelHeader}>보고서 목록</div>
                    <div className={classes.contextPanelBody}>
                        {["월간 매출 리포트", "Q1 고객 분석", "재고 최적화"].map((item, i) => (
                            <div
                                key={item}
                                className={classes.listItem}
                                data-active={i === 0 || undefined}
                                style={i === 0 ? {borderLeftColor: "var(--sage-brand-primary)"} : undefined}
                            >
                                {item}
                            </div>
                        ))}
                    </div>
                </aside>

                <div className={classes.tabsMain}>
                    <div className={classes.mainScroll}>
                        <MockMainContent variant="workspace" primaryColor="var(--sage-brand-primary)"/>
                    </div>
                    <button type="button" className={classes.fab} aria-label="보고서 생성">
                        <IconFilePlus size={24}/>
                    </button>
                </div>
            </div>
        </div>
    );
}
