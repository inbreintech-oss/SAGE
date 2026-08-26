import { useEffect, useState } from "react";
import { Box, Button, Collapse, Group, ScrollArea, Text, UnstyledButton } from "@mantine/core";
import { IconChevronDown, IconDatabase, IconX } from "@tabler/icons-react";
import type { SageData } from "@/features/data";
import { resolvePangeaFieldCount, resolvePangeaSchemaFields } from "@/features/data";
import { CopyableListItemId } from "@/components/copyableListItemId";
import classes from "./reportmanagement.module.css";

export type AnalysisModelEntityCardProps = {
    model: SageData;
    readonly?: boolean;
    onChange?: () => void;
    onClear?: () => void;
};

export function AnalysisModelEntityCard({
    model,
    readonly = false,
    onChange,
    onClear,
}: AnalysisModelEntityCardProps) {
    const fields = resolvePangeaSchemaFields(model);
    const fieldCount = resolvePangeaFieldCount(model);
    const [schemaExpanded, setSchemaExpanded] = useState(false);

    useEffect(() => {
        setSchemaExpanded(false);
    }, [model.did]);

    return (
        <Box className={classes.entityCard}>
            <Group justify="space-between" align="flex-start" wrap="nowrap" mb={6}>
                <Group gap={6}>
                    <IconDatabase size={16} color="#1c7ed6" />
                    <Text className={classes.entityCardTitle}>{model.name}</Text>
                </Group>
                {!readonly && (
                    <Group gap={4}>
                        {onChange && (
                            <Button size="compact-xs" variant="light" onClick={onChange}>
                                변경
                            </Button>
                        )}
                        {onClear && (
                            <Button
                                size="compact-xs"
                                variant="subtle"
                                color="gray"
                                leftSection={<IconX size={12} />}
                                onClick={onClear}
                            >
                                해제
                            </Button>
                        )}
                    </Group>
                )}
            </Group>
            <Text className={classes.entityCardDesc} lineClamp={3}>
                {model.description || "설명 없음"}
            </Text>
            <Box mt={8}>
                <CopyableListItemId
                    label="데이터 모델 등록 ID"
                    value={model.did}
                    copiedMessage="데이터 모델 등록 ID가 복사되었습니다."
                />
            </Box>
            <Box className={classes.schemaPreview}>
                <UnstyledButton
                    className={classes.schemaToggle}
                    onClick={() => setSchemaExpanded(prev => !prev)}
                    aria-expanded={schemaExpanded}
                >
                    <Text size="10px" fw={600} c="dimmed">
                        통합 스키마 표준 매핑 ({fieldCount}건)
                    </Text>
                    <IconChevronDown
                        size={14}
                        className={classes.schemaChevron}
                        data-expanded={schemaExpanded || undefined}
                    />
                </UnstyledButton>
                <Collapse in={schemaExpanded}>
                    {fields.length > 0 ? (
                        <ScrollArea
                            className={classes.pickerSchemaScroll}
                            h={200}
                            type="auto"
                            offsetScrollbars
                        >
                            {fields.map(f => (
                                <Box key={f.name} className={classes.pickerSchemaRow}>
                                    {f.name}
                                </Box>
                            ))}
                        </ScrollArea>
                    ) : (
                        <Text size="xs" c="dimmed">스키마 필드 정보가 없습니다.</Text>
                    )}
                </Collapse>
            </Box>
        </Box>
    );
}
