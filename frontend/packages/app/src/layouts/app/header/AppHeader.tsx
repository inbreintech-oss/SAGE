import React from "react";
import {useMenu} from "@/hooks";
import {Box, Flex, Group, ThemeIcon, Title} from "@mantine/core";
import {AppBreadcrumb, type AppHeaderButtonProps} from "@/components";
import {APP_CONTEXT_HEADER_HEIGHT} from "@/layouts/app/constants";
import classes from "./AppHeader.module.css";

export type AppHeaderProps = Readonly<{
    stepperArea?: React.ReactNode;
    buttonsArea?: React.ReactNode | AppHeaderButtonProps[];
    icon?: React.ReactNode;
    /** 메뉴 breadcrumb 대신 표시할 페이지 제목 (관리 화면 등) */
    title?: string;
}>;

export default function AppHeader({
    stepperArea,
    buttonsArea,
    icon,
    title,
}: AppHeaderProps) {
    const {currentMenu} = useMenu();

    return (
        <Flex
            className={classes.root}
            align="center"
            px="md"
            gap="md"
            h={APP_CONTEXT_HEADER_HEIGHT}
            style={{flexShrink: 0}}
        >
            {title ? (
                <Group justify="space-between" wrap="nowrap" w="100%">
                    <Group gap="xs" wrap="nowrap">
                        {icon && (
                            <ThemeIcon variant="transparent" size={24}>
                                {icon}
                            </ThemeIcon>
                        )}
                        <Title order={3} m={0} style={{fontSize: 15, fontWeight: 600}}>
                            {title}
                        </Title>
                        {stepperArea}
                    </Group>
                    {buttonsArea != null && buttonsArea !== false && (
                        <Group gap="sm">{buttonsArea}</Group>
                    )}
                </Group>
            ) : (
                <Box style={{ flex: 1, width: "100%", minWidth: 0 }}>
                    <AppBreadcrumb
                        currentMenu={currentMenu}
                        stepperArea={stepperArea}
                        buttonArea={buttonsArea}
                        icon={icon}
                    />
                </Box>
            )}
        </Flex>
    );
}
