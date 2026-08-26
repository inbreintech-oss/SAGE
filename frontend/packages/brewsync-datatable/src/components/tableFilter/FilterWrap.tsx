import React from "react";
import {Button, Group, Stack} from "@mantine/core";

export type FilterWrapProps = {
    children?: React.ReactNode;
    onCancel?: React.MouseEventHandler<HTMLButtonElement>;
    onClear?: React.MouseEventHandler<HTMLButtonElement>;
    onSubmit?: React.MouseEventHandler<HTMLButtonElement>;
    hasValue?: boolean;
    buttonsFirst?: boolean;
};

export default function FilterWrap({
    children,
    onCancel,
    onClear,
    onSubmit,
    buttonsFirst = false,
    hasValue,
}: FilterWrapProps) {
    return (
        <Stack gap="xs" p="xs" >
            {!buttonsFirst && (
                children
            )}
            <Group justify="flex-end" gap={"xs"}>
                <Button size="xs" variant="default" onClick={onCancel}>Cancel</Button>
                <Button size="xs" variant="filled" onClick={onSubmit}>Save</Button>
                {hasValue && <Button size="xs" variant="filled" color="red" onClick={onClear}>Clear</Button>}
            </Group>
            {buttonsFirst && (
                children
            )}
        </Stack>
    )
}
