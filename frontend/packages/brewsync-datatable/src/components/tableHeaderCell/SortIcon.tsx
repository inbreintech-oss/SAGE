import {IconSortDescending, IconSortAscending, IconArrowsSort} from "@tabler/icons-react";
import {SortDirection} from "@tanstack/react-table";
import {ActionIcon} from "@mantine/core";
import React from "react";

export type SortIconProps = {
    direction: false | SortDirection;
    onClick?: React.MouseEventHandler<HTMLButtonElement>;
}

export default function SortIcon({
    direction,
    onClick
}: SortIconProps) {
    const renderIcon = () => {
        switch (direction) {
            case "asc":
                return <IconSortAscending size={12} />;
            case "desc":
                return <IconSortDescending size={12} />;
            default:
                return <IconArrowsSort size={12} />;
        }
    }

    return (
        <ActionIcon variant="transparent" size={24} onClick={onClick}>
            {renderIcon()}
        </ActionIcon>
    )
}
