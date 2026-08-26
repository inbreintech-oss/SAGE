import {useEffect, useState} from "react";
import {Button, Loader, Stack, TextInput} from "@mantine/core";
import {useMutation, useQueryClient} from "@tanstack/react-query";
import {IconPlus, IconTrash} from "@tabler/icons-react";
import {notifications} from "@mantine/notifications";
import {
    adminKeys,
    adminMutations,
    useCodeDetails,
    useCodeGroups,
} from "@/features/admin-settings";
import type {CodeDetail, CodeGroup} from "@/features/admin-settings";
import {readTextInputValue, latinInputProps} from "./inputHelpers";
import {
    sanitizeCode,
    validateDetailCode,
    validateDetailName,
    validateGroupCode,
    validateGroupName,
} from "./codeValidation";
import classes from "../adminSettings.module.css";

const emptyGroupForm = {group_code: "", group_name: "", description: ""};
const emptyDetailForm = {code: "", name: "", sort_order: "1"};

function showValidationError(message: string) {
    notifications.show({color: "red", title: "입력 확인", message});
}

export default function CategoryPanel() {
    const qc = useQueryClient();
    const groupsQuery = useCodeGroups();
    const masters = groupsQuery.data ?? [];

    const [activeGroupCode, setActiveGroupCode] = useState("");
    const [selectedDetailId, setSelectedDetailId] = useState<string | null>(null);
    const [groupMode, setGroupMode] = useState<"create" | "edit">("create");
    const [detailMode, setDetailMode] = useState<"create" | "edit">("create");
    const [groupForm, setGroupForm] = useState(emptyGroupForm);
    const [detailForm, setDetailForm] = useState(emptyDetailForm);

    useEffect(() => {
        if (!activeGroupCode && masters.length > 0) {
            setActiveGroupCode(masters[0].group_code);
        }
    }, [masters, activeGroupCode]);

    const detailsQuery = useCodeDetails(activeGroupCode);
    const details = detailsQuery.data ?? [];
    const activeMaster = masters.find((m) => m.group_code === activeGroupCode);

    const invalidateCodes = () => {
        qc.invalidateQueries({queryKey: adminKeys.codeGroups()});
        if (activeGroupCode) {
            qc.invalidateQueries({queryKey: adminKeys.codeDetails(activeGroupCode)});
        }
    };

    const onError = (error: Error) => {
        notifications.show({
            color: "red",
            title: "저장 실패",
            message: error.message || "요청 처리 중 오류가 발생했습니다.",
        });
    };

    const registerGroup = useMutation({
        ...adminMutations.registerCodeGroup(),
        onSuccess: (group) => {
            invalidateCodes();
            setActiveGroupCode(group.group_code);
            setGroupMode("edit");
            setGroupForm({
                group_code: group.group_code,
                group_name: group.group_name,
                description: group.description ?? "",
            });
            notifications.show({color: "teal", message: "그룹 코드가 등록되었습니다."});
        },
        onError,
    });

    const updateGroup = useMutation({
        ...adminMutations.updateCodeGroup(),
        onSuccess: () => {
            invalidateCodes();
            notifications.show({color: "teal", message: "그룹 코드가 저장되었습니다."});
        },
        onError,
    });

    const deleteGroup = useMutation({
        ...adminMutations.deleteCodeGroup(),
        onSuccess: () => {
            invalidateCodes();
            setGroupForm(emptyGroupForm);
            setGroupMode("create");
            setActiveGroupCode("");
            setSelectedDetailId(null);
            setDetailMode("create");
            setDetailForm(emptyDetailForm);
            notifications.show({color: "teal", message: "그룹 코드가 삭제되었습니다."});
        },
        onError,
    });

    const registerDetail = useMutation({
        ...adminMutations.registerCodeDetail(),
        onSuccess: () => {
            invalidateCodes();
            setDetailForm(emptyDetailForm);
            setDetailMode("create");
            setSelectedDetailId(null);
            notifications.show({color: "teal", message: "상세 코드가 등록되었습니다."});
        },
        onError,
    });

    const updateDetail = useMutation({
        ...adminMutations.updateCodeDetail(),
        onSuccess: () => {
            invalidateCodes();
            notifications.show({color: "teal", message: "상세 코드가 저장되었습니다."});
        },
        onError,
    });

    const deleteDetail = useMutation({
        ...adminMutations.deleteCodeDetail(),
        onSuccess: () => {
            invalidateCodes();
            setDetailForm(emptyDetailForm);
            setDetailMode("create");
            setSelectedDetailId(null);
            notifications.show({color: "teal", message: "상세 코드가 삭제되었습니다."});
        },
        onError,
    });

    const selectMaster = (master: CodeGroup) => {
        setActiveGroupCode(master.group_code);
        setSelectedDetailId(null);
        setDetailMode("create");
        setDetailForm(emptyDetailForm);
        setGroupMode("edit");
        setGroupForm({
            group_code: master.group_code,
            group_name: master.group_name,
            description: master.description ?? "",
        });
    };

    const startGroupCreate = () => {
        setGroupMode("create");
        setGroupForm(emptyGroupForm);
    };

    const selectDetail = (detail: CodeDetail) => {
        setSelectedDetailId(detail.detail_id);
        setDetailMode("edit");
        setDetailForm({
            code: detail.code,
            name: detail.name,
            sort_order: String(detail.sort_order),
        });
    };

    const startDetailCreate = () => {
        if (!activeGroupCode) return;
        setDetailMode("create");
        setSelectedDetailCode(null);
        setDetailForm(emptyDetailForm);
    };

    const resetGroupForm = () => {
        if (groupMode === "edit" && activeMaster) {
            setGroupForm({
                group_code: activeMaster.group_code,
                group_name: activeMaster.group_name,
                description: activeMaster.description ?? "",
            });
            return;
        }
        setGroupForm(emptyGroupForm);
    };

    const resetDetailForm = () => {
        if (detailMode === "edit" && selectedDetailId) {
            const detail = details.find((d) => d.detail_id === selectedDetailId);
            if (detail) {
                setDetailForm({
                    code: detail.code,
                    name: detail.name,
                    sort_order: String(detail.sort_order),
                });
                return;
            }
        }
        setDetailForm(emptyDetailForm);
    };

    const saveGroup = () => {
        const groupCode = groupForm.group_code.trim();
        const groupName = groupForm.group_name.trim();

        const nameError = validateGroupName(groupForm.group_name);
        if (nameError) {
            showValidationError(nameError);
            return;
        }

        if (groupMode === "create") {
            const codeError = validateGroupCode(groupForm.group_code);
            if (codeError) {
                showValidationError(codeError);
                return;
            }
            registerGroup.mutate({
                group_code: groupCode,
                group_name: groupName,
                description: groupForm.description,
            });
            return;
        }

        updateGroup.mutate({
            group_code: groupCode,
            group_name: groupName,
            description: groupForm.description,
            use_yn: true,
        });
    };

    const hasDuplicateSortOrder = (sortOrder: number) =>
        details.some(
            (d) => d.sort_order === sortOrder && d.code !== detailForm.code.trim(),
        );

    const saveDetail = () => {
        const codeError = validateDetailCode(detailForm.code);
        if (codeError) {
            showValidationError(codeError);
            return;
        }
        const nameError = validateDetailName(detailForm.name);
        if (nameError) {
            showValidationError(nameError);
            return;
        }

        const sortOrder = Number(detailForm.sort_order) || 1;
        if (hasDuplicateSortOrder(sortOrder)) {
            notifications.show({
                color: "yellow",
                title: "정렬순서 중복",
                message: `정렬순서 ${sortOrder}은(는) 이미 다른 상세 코드에 사용 중입니다.`,
            });
            return;
        }

        const payload = {
            group_code: activeGroupCode,
            code: detailForm.code.trim(),
            name: detailForm.name.trim(),
            sort_order: sortOrder,
        };

        if (detailMode === "create") {
            registerDetail.mutate(payload);
        } else {
            updateDetail.mutate({...payload, use_yn: true});
        }
    };

    const selectedDetail = selectedDetailId
        ? details.find((d) => d.detail_id === selectedDetailId)
        : undefined;

    const isLoading = groupsQuery.isLoading || detailsQuery.isLoading;

    if (isLoading) {
        return (
            <div className={classes.emptyState}>
                <Loader size="sm"/>
            </div>
        );
    }

    if (groupsQuery.isError) {
        return (
            <div className={classes.emptyState}>
                공통코드를 불러오지 못했습니다. SAGE.py 서버와 시드 데이터를 확인하세요.
            </div>
        );
    }

    return (
        <div className={classes.section}>
            <div className={classes.codeSplit}>
                <div className={classes.codePanel}>
                    <div className={classes.codePanelTitleRow}>
                        <span className={classes.codePanelTitle}>그룹 코드 (마스터)</span>
                        <span className={classes.codePanelMeta}>{masters.length}건</span>
                    </div>
                    <div className={`${classes.codePanelBody} ${classes.codeListFixed}`}>
                        {masters.map((m) => (
                            <button
                                key={m.group_code}
                                type="button"
                                className={classes.masterItem}
                                data-active={activeGroupCode === m.group_code || undefined}
                                onClick={() => selectMaster(m)}
                            >
                                <div style={{fontWeight: 600}}>{m.group_name}</div>
                                <div style={{fontSize: 10, opacity: 0.7}}>{m.group_code}</div>
                            </button>
                        ))}
                        {masters.length === 0 && (
                            <div className={classes.codeListEmpty}>등록된 그룹 없음</div>
                        )}
                    </div>
                </div>

                <div className={classes.codePanel}>
                    <div className={classes.codePanelTitleRow}>
                        <span className={classes.codePanelTitle}>
                            상세 코드
                            {activeMaster ? ` - ${activeMaster.group_name}` : ""}
                        </span>
                    </div>
                    <div className={`${classes.codePanelBody} ${classes.codeListFixed}`}>
                        <table className={classes.table}>
                            <thead>
                                <tr>
                                    <th>코드</th>
                                    <th>명칭</th>
                                    <th>정렬</th>
                                </tr>
                            </thead>
                            <tbody>
                                {details.map((d) => (
                                    <tr
                                        key={d.detail_id}
                                        data-clickable
                                        data-selected={selectedDetailId === d.detail_id || undefined}
                                        onClick={() => selectDetail(d)}
                                    >
                                        <td>{d.code}</td>
                                        <td>{d.name}</td>
                                        <td>{d.sort_order}</td>
                                    </tr>
                                ))}
                                {details.length === 0 && (
                                    <tr>
                                        <td colSpan={3} className={classes.codeListEmptyCell}>
                                            상세 코드 없음
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <Stack gap="sm">
                <div className={classes.formCard}>
                    <div className={classes.formTitleRow}>
                        <div className={classes.formTitle}>그룹 코드 등록 / 수정</div>
                        <Button size="compact-xs" variant="light" leftSection={<IconPlus size={12}/>} onClick={startGroupCreate}>
                            신규
                        </Button>
                    </div>
                    <div className={classes.formRowTwoCol}>
                        <TextInput
                            label="그룹코드명"
                            size="xs"
                            value={groupForm.group_name}
                            onChange={(e) =>
                                setGroupForm((f) => ({
                                    ...f,
                                    group_name: readTextInputValue(e),
                                }))
                            }
                        />
                        <TextInput
                            label="그룹코드"
                            size="xs"
                            {...latinInputProps({inputClassName: classes.latinInput})}
                            value={groupForm.group_code}
                            disabled={groupMode === "edit"}
                            onChange={(e) =>
                                setGroupForm((f) => ({
                                    ...f,
                                    group_code: sanitizeCode(readTextInputValue(e)),
                                }))
                            }
                        />
                    </div>
                    <div className={classes.formActions}>
                        {groupMode === "edit" && activeGroupCode && (
                            <Button
                                size="xs"
                                variant="light"
                                color="red"
                                leftSection={<IconTrash size={14}/>}
                                loading={deleteGroup.isPending}
                                onClick={() => deleteGroup.mutate(activeGroupCode)}
                            >
                                삭제
                            </Button>
                        )}
                        <Button size="xs" variant="default" onClick={resetGroupForm}>
                            초기화
                        </Button>
                        <Button
                            size="xs"
                            loading={registerGroup.isPending || updateGroup.isPending}
                            onClick={saveGroup}
                        >
                            저장
                        </Button>
                    </div>
                </div>

                <div className={classes.formCard}>
                    <div className={classes.formTitleRow}>
                        <div className={classes.formTitle}>상세 코드 등록 / 수정</div>
                        <Button
                            size="compact-xs"
                            variant="light"
                            leftSection={<IconPlus size={12}/>}
                            onClick={startDetailCreate}
                            disabled={!activeGroupCode}
                        >
                            신규
                        </Button>
                    </div>
                    <div className={classes.formRowTwoCol}>
                        <TextInput
                            label="코드"
                            size="xs"
                            {...latinInputProps({inputClassName: classes.latinInput})}
                            value={detailForm.code}
                            disabled={detailMode === "edit"}
                            onChange={(e) =>
                                setDetailForm((f) => ({
                                    ...f,
                                    code: sanitizeCode(readTextInputValue(e)),
                                }))
                            }
                        />
                        <TextInput
                            label="명칭"
                            size="xs"
                            value={detailForm.name}
                            onChange={(e) =>
                                setDetailForm((f) => ({
                                    ...f,
                                    name: readTextInputValue(e),
                                }))
                            }
                        />
                    </div>
                    <TextInput
                        label="정렬순서"
                        size="xs"
                        value={detailForm.sort_order}
                        onChange={(e) =>
                            setDetailForm((f) => ({
                                ...f,
                                sort_order: readTextInputValue(e).replace(/\D/g, ""),
                            }))
                        }
                        mt="sm"
                    />
                    <div className={classes.formActions}>
                        {detailMode === "edit" && selectedDetail && (
                            <Button
                                size="xs"
                                variant="light"
                                color="red"
                                leftSection={<IconTrash size={14}/>}
                                loading={deleteDetail.isPending}
                                onClick={() =>
                                    deleteDetail.mutate({
                                        groupCode: activeGroupCode,
                                        code: selectedDetail.code,
                                    })
                                }
                            >
                                삭제
                            </Button>
                        )}
                        <Button size="xs" variant="default" onClick={resetDetailForm}>
                            초기화
                        </Button>
                        <Button
                            size="xs"
                            disabled={!activeGroupCode}
                            loading={registerDetail.isPending || updateDetail.isPending}
                            onClick={saveDetail}
                        >
                            저장
                        </Button>
                    </div>
                </div>
            </Stack>
        </div>
    );
}
