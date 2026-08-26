import {
    IconChartBar,
    IconFileAnalytics,
    IconPlayerPlay,
    IconTrendingUp,
} from "@tabler/icons-react";
import classes from "./layoutPreview.module.css";

type MockMainContentProps = Readonly<{
    variant?: "dashboard" | "workspace";
    primaryColor?: string;
}>;

export default function MockMainContent({
    variant = "dashboard",
    primaryColor = "var(--sage-brand-primary, #0090da)",
}: MockMainContentProps) {
    if (variant === "workspace") {
        return (
            <div className={classes.workspacePanels}>
                <div className={classes.panel}>
                    <div className={classes.panelHeader}>모델 목록</div>
                    <div className={classes.panelBody}>
                        {["월간 매출 분석", "고객 세그먼트", "재고 예측"].map((name, i) => (
                            <div
                                key={name}
                                className={classes.listItem}
                                data-active={i === 0 || undefined}
                                style={i === 0 ? {borderLeftColor: primaryColor} : undefined}
                            >
                                {name}
                            </div>
                        ))}
                    </div>
                </div>
                <div className={classes.panel} style={{flex: 1.4}}>
                    <div className={classes.panelHeader}>에디터</div>
                    <div className={classes.panelBody}>
                        <div className={classes.codeBlock}>
                            SELECT region, SUM(revenue)<br/>
                            FROM sales_monthly<br/>
                            GROUP BY region
                        </div>
                    </div>
                </div>
                <div className={classes.panel}>
                    <div className={classes.panelHeader}>미리보기</div>
                    <div className={classes.panelBody}>
                        <div className={classes.chartPlaceholder}>
                            <IconChartBar size={32} stroke={1.5} color={primaryColor}/>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={classes.dashboardGrid}>
            <div className={classes.kpiRow}>
                {[
                    {label: "등록 모델", value: "24", delta: "+3"},
                    {label: "보고서", value: "156", delta: "+12"},
                    {label: "실행 중", value: "3", delta: "●"},
                    {label: "완료율", value: "94%", delta: "+2%"},
                ].map((kpi) => (
                    <div key={kpi.label} className={classes.kpiCard}>
                        <span className={classes.kpiLabel}>{kpi.label}</span>
                        <span className={classes.kpiValue}>{kpi.value}</span>
                        <span className={classes.kpiDelta} style={{color: primaryColor}}>{kpi.delta}</span>
                    </div>
                ))}
            </div>
            <div className={classes.chartCard}>
                <div className={classes.chartCardHeader}>
                    <span>월별 보고서 생성 추이</span>
                    <IconTrendingUp size={16} color={primaryColor}/>
                </div>
                <div className={classes.chartBars}>
                    {[40, 65, 45, 80, 55, 90, 70, 85, 60, 95, 75, 88].map((h, i) => (
                        <div
                            key={i}
                            className={classes.chartBar}
                            style={{height: `${h}%`, backgroundColor: primaryColor, opacity: 0.7 + (i % 3) * 0.1}}
                        />
                    ))}
                </div>
            </div>
            <div className={classes.recentCard}>
                <div className={classes.chartCardHeader}>
                    <span>최근 보고서</span>
                    <IconFileAnalytics size={16} color={primaryColor}/>
                </div>
                {["2026 Q1 매출 리포트", "고객 이탈 분석", "재고 최적화 보고서"].map((title) => (
                    <div key={title} className={classes.recentRow}>{title}</div>
                ))}
            </div>
        </div>
    );
}

export function ExecuteButton({color = "var(--sage-brand-primary)"}: Readonly<{color?: string}>) {
    return (
        <button type="button" className={classes.executeBtn} style={{backgroundColor: color}}>
            <IconPlayerPlay size={14}/>
            실행
        </button>
    );
}
