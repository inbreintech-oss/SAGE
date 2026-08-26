import React from "react";
import type {Menu} from "@/libs/types";
import {Box, Button, type ButtonProps, Group} from "@mantine/core";
import AppBreadcrumbItem from "@/components/breadcrumb/AppBreadcrumbItem.tsx";

/**
 * 메뉴 Breadcrumb Props
 */
export type AppBreadCrumbProps = Readonly<{
    currentMenu?: Menu | null;
    icon?: React.ReactNode;
    stepperArea?: React.ReactNode;
    buttonArea?: React.ReactNode | AppHeaderButtonProps[];
}>;

export type AppHeaderButtonProps = {
    label: string;
    onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
} & Omit<ButtonProps, "onClick">;

/**
 * 메뉴 Breadcrumb 입니다.
 * @constructor
 */
export default function AppBreadcrumb({
    currentMenu,
    icon,
    stepperArea,
    buttonArea
}: AppBreadCrumbProps) {

    const renderButtons = () => {
        if (!buttonArea) return null;
        if (Array.isArray(buttonArea)) {
            return buttonArea.map((btn, index) => (
                <Button key={index} size="xs" {...btn}>
                    {btn.label}
                </Button>
            ));
        }
        return buttonArea;
    }

    return (
        <Group w="100%" wrap="nowrap" align="center">
            {currentMenu && (
                <AppBreadcrumbItem menuData={currentMenu} icon={icon} />
            )}
            <Box h="100%">
                {stepperArea}
            </Box>
            <Group ml="auto" gap="sm" wrap="nowrap" style={{ flexShrink: 0 }}>
                {renderButtons()}
            </Group>
        </Group>
    )
}
