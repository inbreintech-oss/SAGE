import { type ContextModalProps } from "@mantine/modals"
import React from "react";
import {ActionIcon, Button, Text} from "@mantine/core";

interface ITestMModalProps {
    text?: string;
    icon?: React.ReactNode;
}

export default function TestModal({
    context,
    id,
    innerProps
}: ContextModalProps<ITestMModalProps>) {
    const { text, icon } = innerProps;

    return (
        <>
            {text && (
                <Text>{text}</Text>
            )}
            {icon && (
                <ActionIcon>
                    {icon}
                </ActionIcon>
            )}
            <Button fullWidth mt="md" onClick={() => context.closeModal(id)}>
                닫기
            </Button>
        </>
    )
}