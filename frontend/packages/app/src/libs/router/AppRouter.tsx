import {lazy, type ReactNode} from "react";
import {BrowserRouter, Route, Routes} from "react-router-dom";
import {Loadable} from "@/components";
import AppPage from "@/pages/AppPage";
import AdminSettingsPage from "@/pages/admin/AdminSettingsPage";

const DashboardPage = Loadable(lazy(() => import("@/pages/DashboardPage")));
const NotFoundPage = Loadable(lazy(() => import("@/pages/NotFoundPage")));

/* SAG-E Pages */
const DataManagementPage = Loadable(lazy(() => import("@/pages/data/DataManagementPage.tsx")));
const ToolManagementPage = Loadable(lazy(() => import("@/pages/tool/ToolManagementPage.tsx")));

/* Report Pages */
const ReportManagementPage = Loadable(lazy(() => import("@/pages/report/reportmanagement/ReportManagementPage.tsx")));
const ReportListBrowsePage = Loadable(lazy(() => import("@/pages/report/reportlist/ReportListBrowsePage.tsx")));
const LayoutPreviewPage = Loadable(lazy(() => import("@/pages/layout-preview/LayoutPreviewPage.tsx")));

/* ============================================
   Route Configuration Types
   ============================================ */

type RouteConfig = {
    path: string;
    component: ReactNode;
};

/* ============================================
   Route Definitions by Access Level
   ============================================ */

/**
 * Route configurations
 */
const routeConfigs: RouteConfig[] = [
    {path: "/", component: <DashboardPage/>},
    {path: "datamanagement", component: <DataManagementPage />},
    {path: "toolmanagement", component: <ToolManagementPage />},
    {path: "report/reportmanagement", component: <ReportManagementPage />},
    {path: "report/reportlist", component: <ReportListBrowsePage />},
];

/* ============================================
   Route Renderer Helpers
   ============================================ */

const renderRoute = (route: RouteConfig) => {
    return route.path === "/" ? (
        <Route key={route.path} index element={route.component}/>
    ) : (
        <Route key={route.path} path={route.path} element={route.component}/>
    );
};

/* ============================================
   AppRouter Component
   ============================================ */

export default function AppRouter() {
    return (
        <BrowserRouter>
            <Routes>
                {/* 기존 AppShell 밖 — 레이아웃 미리보기 전용 */}
                <Route path="/layout-preview" element={<LayoutPreviewPage/>}/>
                <Route path="/" element={<AppPage />}>
                    {routeConfigs.map(renderRoute)}
                    {/* 설정 Mock — 명시 라우트 (중첩 path 매칭 보강) */}
                    <Route path="admin/settings" element={<AdminSettingsPage/>}/>
                    <Route path="*" element={<NotFoundPage/>}/>
                </Route>
            </Routes>
        </BrowserRouter>
    );
}
