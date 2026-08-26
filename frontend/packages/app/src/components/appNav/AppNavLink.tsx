import React from "react";
import {NavLink, type NavLinkProps} from "@mantine/core";
import {NavLink as RouterLink} from "react-router-dom";
import type {Menu} from "@/libs/types";
import { getMenuIcon } from "@/libs/menuIconMap";
import classes from "./AppNav.module.css";

/**
 * AppNavLink Props
 */
export type AppNavLinkProps = Readonly<{
    children?: React.ReactNode;
    menuData: Menu;
    defaultOpened?: boolean;
    active?: boolean;
    compact?: boolean;
}>;

/**
 * AppNav에서 사용하는 NavLink 컴포넌트입니다.
 */
export default function AppNavLink({
    children,
    menuData,
    defaultOpened = false,
    active = false,
    compact = false,
}: AppNavLinkProps) {
    const { id, url, korMenuName } = menuData;

    const props: NavLinkProps = {
        label: compact ? undefined : korMenuName,
        active: active,
        leftSection: getMenuIcon(url, korMenuName),
        classNames: {
            root: compact ? `${classes.root} ${classes.rootCompact}` : classes.root,
            section: compact ? `${classes.section} ${classes.sectionCompact}` : classes.section,
            body: compact ? classes.bodyCompact : undefined,
            label: compact ? classes.labelHidden : classes.label,
            chevron: compact ? classes.chevronHidden : undefined,
            children: compact ? classes.childrenCompact : undefined,
        },
        styles: compact ? {
            root: {justifyContent: "center"},
            section: {marginInlineEnd: 0},
        } : undefined,
    }

    return children !== undefined ? (
        <NavLink key={id}
                 active={active}
                 defaultOpened={defaultOpened || active}
                 {...props}
        >
            {children}
        </NavLink>
    ) : (
        <NavLink key={id}
                 to={url || "#"}
                 active={active}
                 component={RouterLink}
                 {...props}
        />
    )
}
