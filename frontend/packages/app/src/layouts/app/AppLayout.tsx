import React, {useState} from "react";
import classes from "./AppLayout.module.css";
import {
    APP_RAIL_WIDTH_COLLAPSED,
    APP_RAIL_WIDTH_EXPANDED,
} from "@/layouts/app/constants";
import {AppNavBar} from "@/layouts/app/navigation";
import {AppTopBar} from "@/layouts/app/header";

export type AppLayoutProps = Readonly<{
    children?: React.ReactNode;
}>;

/**
 * 관리 애플리케이션 Shell — Light Top Bar + Icon Rail + Main (flex, 권장안 ④)
 */
export default function AppLayout({children}: AppLayoutProps) {
    const [railExpanded, setRailExpanded] = useState(false);

    return (
        <div className={classes.root}>
            <AppTopBar/>

            <div className={classes.body}>
                <nav
                    className={classes.rail}
                    data-expanded={railExpanded || undefined}
                    style={{
                        width: railExpanded ? APP_RAIL_WIDTH_EXPANDED : APP_RAIL_WIDTH_COLLAPSED,
                    }}
                    onMouseEnter={() => setRailExpanded(true)}
                    onMouseLeave={() => setRailExpanded(false)}
                    aria-label="주 메뉴"
                >
                    <AppNavBar compact={!railExpanded}/>
                </nav>

                <main className={classes.pageMain}>
                    {children}
                </main>
            </div>
        </div>
    );
}
