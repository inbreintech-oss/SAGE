import React from "react";
import type {Menu} from "@/libs/types";
import {Group, Text, ThemeIcon, Title} from "@mantine/core";

export type BreadcrumbItemProps = {
    icon?: React.ReactNode;
    menuData: Menu;
};

export default function AppBreadcrumbItem({
    icon, menuData
}: BreadcrumbItemProps) {
    return (
        <Group align="center" gap="xs" mr="xl">
            {icon && (
                <ThemeIcon c="blue" variant="transparent">
                    {icon}
                </ThemeIcon>
            )}
            <Title order={3} c="#333333">{menuData.korMenuName}</Title>
            <Text size="xs"
                  style={{alignSelf: "flex-end"}}
                  c="gray"
            >
                v1.0 UI Spec
            </Text>
        </Group>
    )
}