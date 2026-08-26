import React from "react";
import {isEqual} from "lodash";
import {AppNavLink} from "@/components";
import type {Menu} from "@/libs/types";
import {Center, Loader} from "@mantine/core";
import {getMenuPath} from "@/libs/Utils";
import classes from "./AppNav.module.css";

/**
 * App Navigation Props
 */
export type AppNavProps = Readonly<{
    menus?: Menu[];
    currentMenu?: Menu | null;
    isLoading?: boolean;
    /** Icon Rail 접힘 */
    compact?: boolean;
}>

/**
 * App Navigation 컴포넌트 입니다.
 */
const AppNav = function ({
    menus = [],
    currentMenu,
    isLoading = false,
    compact = false,
}: AppNavProps) {
    const rootMenus = menus.filter(menu => !menu.parentId);
    const activeMenus = getMenuPath(menus, currentMenu?.id || -1);

    // 재귀적으로 메뉴를 렌더링하는 함수
    const renderMenu = (menu: Menu) => {
        const children = menus.filter(m => m.parentId === menu.id);
        const isActive = activeMenus.includes(menu);

        // URL 없고 자식이 있는 최상위 메뉴 → 섹션 헤더 레이블로 렌더링
        const isSectionHeader = !menu.url && !menu.parentId && children.length > 0;

        if (isSectionHeader) {
            return (
                <React.Fragment key={menu.id}>
                    <div className={compact ? classes.sectionLabelHidden : classes.sectionLabel}>
                        {menu.korMenuName}
                    </div>
                    {children.map(child => renderMenu(child))}
                </React.Fragment>
            );
        }

        if (children.length === 0) {
            return (
                <AppNavLink key={menu.id}
                            menuData={menu}
                            active={isActive}
                            compact={compact}
                />
            )
        } else {
            return (
                <AppNavLink key={menu.id}
                            menuData={menu}
                            active={isActive}
                            compact={compact}
                >
                    {children.map(child => renderMenu(child))}
                </AppNavLink>
            )
        }
    }

    return (
        <>
            {isLoading ?
                <Center w="100%" h="100%" py="md"><Loader size="sm"/></Center>:
                rootMenus.map(root => renderMenu(root))
            }
        </>
    )
}

export default React.memo(AppNav, (prev, next) => {
    return (
        prev.isLoading === next.isLoading &&
        prev.compact === next.compact &&
        prev.currentMenu?.id === next.currentMenu?.id &&
        isEqual(prev.menus, next.menus)
    )
});
