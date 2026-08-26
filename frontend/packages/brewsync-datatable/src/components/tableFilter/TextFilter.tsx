import React from "react";
import {CloseButton, TextInput} from "@mantine/core";
import {FilterBaseProps} from "./FilterBase";
import FilterWrap from "./FilterWrap";

export type TextFilterProps = {} & FilterBaseProps;

export default function TextFilter({
    ref,
    value,
    onSubmit,
    onDismiss,
    onReset,
}: TextFilterProps) {
    const [filterText, setFilterText] = React.useState<string>(String(value || ""));

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            onSubmit?.(filterText);
        } else if (e.key === "Escape") {
            onDismiss?.();
        }
    }

    const clearButton = () => {
        return (
            <CloseButton size="xs"
                         onClick={() => {
                             setFilterText("");
                             ref?.current?.focus();
                         }}
            />
        )
    }

    return (
        <FilterWrap onSubmit={() => onSubmit?.(filterText)}
                    onCancel={() => onDismiss?.()}
                    onClear={() => onReset?.()}
                    hasValue={value !== undefined}
        >
            <TextInput ref={ref}
                       value={filterText}
                       onInput={e => setFilterText(e.currentTarget.value)}
                       onKeyDown={handleKeyDown}
                       size="xs"
                       rightSection={filterText.length > 0 ? clearButton() : undefined}
                       data-autofocus
            />
        </FilterWrap>
    )
}
