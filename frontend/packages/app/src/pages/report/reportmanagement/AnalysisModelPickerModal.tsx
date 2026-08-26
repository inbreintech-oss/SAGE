import { useMemo, useState } from "react";
import {
    Box,
    Button,
    Center,
    Group,
    Loader,
    Modal,
    ScrollArea,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import type { SageData } from "@/features/data";
import { resolvePangeaFieldCount, resolvePangeaSchemaFields } from "@/features/data";
import { CopyableListItemId } from "@/components/copyableListItemId";
import classes from "./reportmanagement.module.css";

export type AnalysisModelPickerModalProps = {
    opened: boolean;
    onClose: () => void;
    models: SageData[];
    isLoading: boolean;
    isError: boolean;
    selectedDid: string | null;
    onSelect: (model: SageData) => void;
    onReload?: () => void;
};

export function AnalysisModelPickerModal({
    opened,
    onClose,
    models,
    isLoading,
    isError,
    selectedDid,
    onSelect,
    onReload,
}: AnalysisModelPickerModalProps) {
    const [searchRaw, setSearchRaw] = useState("");
    const [previewDid, setPreviewDid] = useState<string | null>(selectedDid);

    const filtered = useMemo(() => {
        const q = searchRaw.trim().toLowerCase();
        if (!q) return models;
        return models.filter(
            m => m.name.toLowerCase().includes(q)
                || (m.description ?? "").toLowerCase().includes(q),
        );
    }, [models, searchRaw]);

    const previewModel = filtered.find(m => m.did === previewDid) ?? filtered[0] ?? null;
    const previewFields = previewModel ? resolvePangeaSchemaFields(previewModel) : [];

    const handleConfirm = () => {
        if (!previewModel) return;
        onSelect(previewModel);
        onClose();
    };

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title="분석모델 조회/선택"
            size="lg"
            centered
        >
            <Stack gap="sm">
                <TextInput
                    size="xs"
                    placeholder="분석모델 검색..."
                    leftSection={<IconSearch size={14} />}
                    value={searchRaw}
                    onChange={e => setSearchRaw(e.currentTarget.value)}
                />

                {isLoading ? (
                    <Center py="lg"><Loader size="sm" /></Center>
                ) : isError ? (
                    <Center py="lg">
                        <Stack align="center" gap="xs">
                            <Text size="sm" c="dimmed">분석모델 목록을 불러오지 못했습니다.</Text>
                            {onReload && (
                                <Button size="xs" variant="light" onClick={onReload}>다시 시도</Button>
                            )}
                        </Stack>
                    </Center>
                ) : filtered.length === 0 ? (
                    <Text size="sm" c="dimmed" ta="center" py="lg">
                        {searchRaw.trim()
                            ? "검색 결과가 없습니다."
                            : "completed 상태 분석모델이 없습니다."}
                    </Text>
                ) : (
                    <Box className={classes.pickerBody}>
                        <Box className={classes.pickerModelColumn}>
                            <Text className={classes.pickerColumnTitle}>분석모델 목록</Text>
                            <ScrollArea className={classes.pickerModelScroll} h={320} type="auto" offsetScrollbars>
                                {filtered.map(model => {
                                    const active = previewDid === model.did;
                                    return (
                                        <Box
                                            key={model.did}
                                            className={`${classes.pickerListItem} ${active ? classes.pickerListItemActive : ""}`}
                                            onClick={() => setPreviewDid(model.did)}
                                        >
                                            <Text size="sm" fw={600} lineClamp={1}>{model.name}</Text>
                                            <Text size="xs" c="dimmed" lineClamp={2} mt={4}>
                                                {model.description || "설명 없음"}
                                            </Text>
                                            <Text size="10px" c="dimmed" mt={4}>
                                                스키마 {resolvePangeaFieldCount(model)}건
                                            </Text>
                                        </Box>
                                    );
                                })}
                            </ScrollArea>
                        </Box>

                        {previewModel && (
                            <Box className={classes.pickerSchemaColumn}>
                                <Text className={classes.pickerColumnTitle}>표준 스키마 미리보기</Text>
                                <Box className={classes.pickerSchemaMeta}>
                                    <CopyableListItemId
                                        label="DID"
                                        value={previewModel.did}
                                        copiedMessage="복사되었습니다."
                                    />
                                </Box>
                                <ScrollArea
                                    className={classes.pickerSchemaScroll}
                                    h={320}
                                    type="auto"
                                    offsetScrollbars
                                >
                                    {previewFields.length > 0 ? (
                                        previewFields.map(f => (
                                            <Box key={f.name} className={classes.pickerSchemaRow}>
                                                {f.name}
                                            </Box>
                                        ))
                                    ) : (
                                        <Text size="xs" c="dimmed" px={10} py={8}>스키마 정보 없음</Text>
                                    )}
                                </ScrollArea>
                            </Box>
                        )}
                    </Box>
                )}

                <Group justify="flex-end" mt="sm">
                    <Button variant="default" size="xs" onClick={onClose}>취소</Button>
                    <Button size="xs" onClick={handleConfirm} disabled={!previewModel}>
                        선택
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
