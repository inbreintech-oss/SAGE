/**
 * menuIconMap.tsx
 * ──────────────────────────────────────────────────────────────────
 * URL 경로 → 사이드바 메뉴 아이콘 매핑 테이블
 * 1차: URL 기반 매핑 (정확한 경로 일치)
 * 2차: 메뉴명(korMenuName) 기반 fallback 매핑
 * 아이콘 소스: @tabler/icons-react
 * ──────────────────────────────────────────────────────────────────
 */
import type { ReactNode } from "react";
import {
    IconChartBar,
    IconDatabase,
    IconDiamond,
    IconLayoutDashboard,
    IconList,
    IconSettings,
    IconTool,
    IconTools,
} from "@tabler/icons-react";

/** 사이드바 메뉴명(16px)과 시각적으로 맞춘 아이콘 크기 */
const MENU_ICON_SIZE = 18;

/** URL → 아이콘 매핑 테이블 */
const menuIconByUrl: Record<string, ReactNode> = {
    "/":                <IconLayoutDashboard size={MENU_ICON_SIZE} />,
    "/datamanagement":  <IconDatabase        size={MENU_ICON_SIZE} />,
    "/toolmanagement":  <IconTools           size={MENU_ICON_SIZE} />,
    "/report/reportmanagement": <IconChartBar size={MENU_ICON_SIZE} />,
    "/report/reportlist": <IconList          size={MENU_ICON_SIZE} />,

    /* 핵심 자산 / 도구 관리 가능 URL 패턴 (백엔드 연동 시 정확한 경로로 교체) */
    "/asset":           <IconDiamond         size={MENU_ICON_SIZE} />,
    "/asset/settings":  <IconDiamond         size={MENU_ICON_SIZE} />,
    "/settings":        <IconSettings        size={MENU_ICON_SIZE} />,
    "/tool":            <IconTools           size={MENU_ICON_SIZE} />,
    "/tool/management": <IconTools           size={MENU_ICON_SIZE} />,
    "/api":             <IconTool            size={MENU_ICON_SIZE} />,
    "/api/management":  <IconTool            size={MENU_ICON_SIZE} />,
};

/** korMenuName → 아이콘 fallback 테이블 (URL이 없거나 매핑 누락 시 사용) */
const menuIconByName: Record<string, ReactNode> = {
    "대시보드":         <IconLayoutDashboard size={MENU_ICON_SIZE} />,
    "데이터 분석 모델":   <IconDatabase        size={MENU_ICON_SIZE} />,
    "데이터분석모델":     <IconDatabase        size={MENU_ICON_SIZE} />,
    "보고서":             <IconChartBar        size={MENU_ICON_SIZE} />,
    "보고서 목록":        <IconList            size={MENU_ICON_SIZE} />,
    "보고서목록":         <IconList            size={MENU_ICON_SIZE} />,
    "핵심 자산 설정":     <IconDiamond         size={MENU_ICON_SIZE} />,
    "핵심자산설정":       <IconDiamond         size={MENU_ICON_SIZE} />,
    "도구(Tool)":         <IconTools           size={MENU_ICON_SIZE} />,
    "도구Tool":           <IconTools           size={MENU_ICON_SIZE} />,
    "API 관리":         <IconTool            size={MENU_ICON_SIZE} />,
};

/**
 * URL 또는 메뉴명으로 사이드바 아이콘을 반환합니다.
 * - url이 있으면 URL 테이블 우선 조회
 * - URL 미매핑 시 korMenuName 테이블로 fallback
 * - 둘 다 없으면 undefined 반환
 */
export function getMenuIcon(url?: string, korMenuName?: string): ReactNode | undefined {
    if (url) {
        const byUrl = menuIconByUrl[url];
        if (byUrl !== undefined) return byUrl;
    }
    if (korMenuName) {
        const trimmed = korMenuName.trim();
        return menuIconByName[trimmed] ?? undefined;
    }
    return undefined;
}
