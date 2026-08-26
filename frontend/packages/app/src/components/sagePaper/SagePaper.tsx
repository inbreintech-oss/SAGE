import React from "react";
import {Group, Paper, type PaperProps, Stack, ThemeIcon, Title} from "@mantine/core";

export type SagePaperProps = {
    children?: React.ReactNode;
} & Omit<PaperProps, "children">;

export default function SagePaper({
    children,
    ...rest
}: SagePaperProps) {
    return (
        <Paper p="md" bg="var(--sage-surface-card)" {...rest}>
            <Stack gap="md" h="100%">
                {children}
            </Stack>
        </Paper>
    )
}

export type SagePaperContentProps = {
    icon?: React.ReactNode;
    title?: string;
    children?: React.ReactNode;
}

function SagePaperContent({
    icon,
    title,
    children,
}: SagePaperContentProps) {
    return (
        <>
            {(icon || title) && (
                <Group align="center" gap="xs">
                    {icon && (
                            <ThemeIcon variant="transparent" size={24}>
                                {icon}
                            </ThemeIcon>
                    )}
                    <Title order={3} m={0}>{title}</Title>
                </Group>
            )}
                {children}
        </>
    )
}

SagePaper.Content = SagePaperContent;