import React from "react";
import {Checkbox, Group, type RenderTreeNodePayload} from "@mantine/core";
import {IconChevronDown} from "@tabler/icons-react";
import type {TreeMode} from "./Tree.tsx";

export type TreeNodePayload = RenderTreeNodePayload & {
    selectOne?: boolean;
    mode?: TreeMode;
}

export default function TreeNode({
    tree,
    node,
    expanded,
    hasChildren,
    elementProps,
    selectOne,
    mode = "check",
}: TreeNodePayload) {
    const checked = tree.isNodeChecked(node.value);
    const indeterminate = tree.isNodeIndeterminate(node.value);

    const handleCheckboxClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (checked) {
            tree.uncheckNode(node.value);
        } else {
            if (selectOne) {
                tree.setCheckedState([node.value]);
            } else {
                tree.checkNode(node.value);
            }
        }
    }

    const handleNodeClick = (e: React.MouseEvent) => {
        if (mode === "select") {
            handleCheckboxClick(e);
            return;
        }

        if (!hasChildren) {
            handleCheckboxClick(e);
            return;
        }
    }

    const handleChevronClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        tree.toggleExpanded(node.value);
    }

    const isSelected = mode === "select" && checked;

    return (
        <Group gap="xs" flex={1} {...elementProps}
               bg={isSelected ? "var(--mantine-color-blue-light)" : undefined}
               style={{
                   ...elementProps.style,
                   cursor: "pointer",
               }}
               onClick={handleNodeClick}
        >
            {mode === "check" && (
                <Checkbox.Indicator checked={checked}
                                    indeterminate={indeterminate}
                                    onClick={handleCheckboxClick}
                                    style={{
                                        cursor: "pointer",
                                    }}
                />
            )}
            <Group gap={5}>
                <span>{node.label}</span>

                {hasChildren && (
                    <IconChevronDown size={14}
                                     onClick={handleChevronClick}
                                     style={{transform: expanded ? "rotate(180deg)" : "rotate(0deg)"}} />
                )}
            </Group>
        </Group>
    )
}
