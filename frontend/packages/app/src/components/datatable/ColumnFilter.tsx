import React, {useState} from "react";
import {Button, Group, Stack, TextInput} from "@mantine/core";

export type ColumnFilterProps = Readonly<{
    label?: string;
    initialValue?: string;
    close?: () => void;
    onCloseClick?: () => void;
    onApplyClick?: (filterText: string) => void;
}>

export default function ColumnFilter({
    label,
    initialValue = "",
    onCloseClick,
    onApplyClick,
}: ColumnFilterProps) {
    const [filterText, setFilterText] = useState<string>(initialValue);

    const keyDownHandler = (e: React.KeyboardEvent<HTMLInputElement>) => {
        // Enter 키를 누르면 필터 적용
        if (e.key === "Enter") {
            onApplyClick?.(filterText);
            return;
        }

        // Escape 키를 누르면 필터 닫기
        if (e.key === "Escape") {
            onCloseClick?.();
            return;
        }
    };

    return (
        <Stack gap="sm">
            <TextInput label={label}
                       size="xs"
                       value={filterText}
                       onKeyDown={keyDownHandler}
                       onChange={e => setFilterText(e.currentTarget.value)}
            />
            <Group justify="end" gap="xs">
                <Button size="compact-sm" onClick={onCloseClick}>
                    취소
                </Button>
                <Button size="compact-sm" onClick={() => onApplyClick?.(filterText)}>
                    적용
                </Button>
            </Group>
        </Stack>
    )
}
