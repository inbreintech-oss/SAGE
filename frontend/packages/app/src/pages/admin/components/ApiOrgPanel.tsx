import {useState} from "react";
import {ActionIcon, Button, Loader, TextInput} from "@mantine/core";
import {useMutation, useQueryClient} from "@tanstack/react-query";
import {notifications} from "@mantine/notifications";
import {IconEye, IconEyeOff, IconPlus, IconTrash} from "@tabler/icons-react";
import {
    adminKeys,
    adminMutations,
    useApiOrganizations,
} from "@/features/admin-settings";
import type {ApiOrganization} from "@/features/admin-settings";
import {readTextInputValue, latinInputProps} from "./inputHelpers";
import classes from "../adminSettings.module.css";

type KeyDraft = {id: string; keyName: string; value: string; showValue: boolean};

function toDrafts(org: ApiOrganization): KeyDraft[] {
    if (org.auth_keys.length === 0) {
        return [{id: "new-1", keyName: "", value: "", showValue: false}];
    }
    return org.auth_keys.map((k, index) => ({
        id: `${org.org_id}-${index}`,
        keyName: k.key_name,
        value: "",
        showValue: false,
    }));
}

export default function ApiOrgPanel() {
    const qc = useQueryClient();
    const orgsQuery = useApiOrganizations();
    const orgs = orgsQuery.data ?? [];

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const isCreateMode = selectedId === null;

    const [name, setName] = useState("");
    const [code, setCode] = useState("");
    const [baseUrl, setBaseUrl] = useState("");
    const [keys, setKeys] = useState<KeyDraft[]>([{id: "new-1", keyName: "", value: "", showValue: false}]);
    const [unlockedKeyFields, setUnlockedKeyFields] = useState<Set<string>>(new Set());

    const unlockKeyField = (id: string) => {
        setUnlockedKeyFields((prev) => {
            if (prev.has(id)) return prev;
            const next = new Set(prev);
            next.add(id);
            return next;
        });
    };

    const resetKeyFieldLocks = () => setUnlockedKeyFields(new Set());

    const selectOrg = (org: ApiOrganization) => {
        setSelectedId(org.org_id);
        setName(org.name);
        setCode(org.code);
        setBaseUrl(org.base_url);
        setKeys(toDrafts(org));
        resetKeyFieldLocks();
    };

    const startCreate = () => {
        setSelectedId(null);
        setName("");
        setCode("");
        setBaseUrl("");
        setKeys([{id: `new-${Date.now()}`, keyName: "", value: "", showValue: false}]);
        resetKeyFieldLocks();
    };

    const invalidate = () => qc.invalidateQueries({queryKey: adminKeys.orgs()});

    const onError = (error: Error) => {
        notifications.show({
            color: "red",
            title: "기관 처리 실패",
            message: error.message || "요청 처리 중 오류가 발생했습니다.",
        });
    };

    const registerOrg = useMutation({
        ...adminMutations.registerOrg(),
        onSuccess: (org) => {
            invalidate();
            selectOrg(org);
            notifications.show({color: "teal", message: "기관이 등록되었습니다."});
        },
        onError,
    });

    const updateOrg = useMutation({
        ...adminMutations.updateOrg(),
        onSuccess: () => {
            invalidate();
            notifications.show({color: "teal", message: "기관 정보가 저장되었습니다."});
        },
        onError,
    });

    const deleteOrg = useMutation({
        ...adminMutations.deleteOrg(),
        onSuccess: () => {
            invalidate();
            startCreate();
            notifications.show({color: "teal", message: "기관이 삭제되었습니다."});
        },
        onError,
    });

    const addKey = () => {
        setKeys((prev) => [...prev, {id: `new-${Date.now()}`, keyName: "", value: "", showValue: false}]);
    };

    const removeKey = (id: string) => {
        setKeys((prev) => prev.filter((k) => k.id !== id));
    };

    const updateKey = (id: string, patch: Partial<Pick<KeyDraft, "keyName" | "value" | "showValue">>) => {
        setKeys((prev) => prev.map((k) => (k.id === id ? {...k, ...patch} : k)));
    };

    const buildKeysPayload = () =>
        keys
            .filter((k) => k.keyName.trim())
            .map((k) => ({key_name: k.keyName.trim(), key_value: k.value}));

    const isDuplicateOrgCode = (orgCode: string) =>
        orgs.some((o) => o.code === orgCode && o.org_id !== selectedId);

    const handleSave = () => {
        const orgCode = code.trim();
        if (!orgCode) {
            notifications.show({color: "red", message: "기관코드를 입력해 주세요."});
            return;
        }
        if (isDuplicateOrgCode(orgCode)) {
            notifications.show({
                color: "red",
                title: "기관코드 중복",
                message: "이미 등록된 기관코드입니다. 다른 코드를 사용해 주세요.",
            });
            return;
        }

        const payload = {
            name: name.trim(),
            code: orgCode,
            base_url: baseUrl.trim(),
            keys: buildKeysPayload(),
        };

        if (isCreateMode) {
            registerOrg.mutate(payload);
        } else if (selectedId) {
            updateOrg.mutate({org_id: selectedId, ...payload});
        }
    };

    if (orgsQuery.isLoading) {
        return <div className={classes.emptyState}><Loader size="sm"/></div>;
    }

    if (orgsQuery.isError) {
        return (
            <div className={classes.emptyState}>
                API 연계 기관 목록을 불러오지 못했습니다. 로그인 상태와 SAGE.py 서버를 확인하세요.
            </div>
        );
    }

    return (
        <div className={classes.section}>
            <div className={classes.codePanel}>
                <div className={classes.codePanelTitleRow}>
                    <span className={classes.codePanelTitle}>등록 기관</span>
                    <span className={classes.codePanelMeta}>{orgs.length}곳</span>
                </div>
                <div className={`${classes.codePanelBody} ${classes.codeListFixed}`}>
                    {orgs.length === 0 ? (
                        <div className={classes.codeListEmpty}>등록된 기관이 없습니다.</div>
                    ) : (
                        <table className={classes.table}>
                            <thead>
                                <tr>
                                    <th>기관명</th>
                                    <th>기관코드</th>
                                    <th>기본 URL</th>
                                </tr>
                            </thead>
                            <tbody>
                                {orgs.map((org) => (
                                    <tr
                                        key={org.org_id}
                                        data-clickable
                                        data-selected={selectedId === org.org_id || undefined}
                                        onClick={() => selectOrg(org)}
                                    >
                                        <td title={org.name}>{org.name}</td>
                                        <td title={org.code}>{org.code}</td>
                                        <td title={org.base_url || undefined}>{org.base_url || "—"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            <div className={classes.formCard}>
                <div className={classes.formTitleRow}>
                    <div className={classes.formTitle}>
                        {isCreateMode ? "기관 등록" : "기관 상세"}
                    </div>
                    <Button size="compact-xs" variant="light" leftSection={<IconPlus size={12}/>} onClick={startCreate}>
                        기관 추가
                    </Button>
                </div>
                <p className={classes.formHint}>
                    인증키는 다건 등록 가능. 조회 값은 마스킹 표시됩니다.
                </p>
                <div style={{display: "grid", gap: 8}}>
                    <div className={classes.formRowTwoCol}>
                        <TextInput
                            label="기관명"
                            size="xs"
                            autoComplete="organization"
                            value={name}
                            onChange={(e) => setName(readTextInputValue(e))}
                        />
                        <TextInput
                            label="기관코드"
                            size="xs"
                            autoComplete="off"
                            {...latinInputProps({inputClassName: classes.latinInput})}
                            value={code}
                            disabled={!isCreateMode}
                            onChange={(e) => setCode(readTextInputValue(e))}
                        />
                    </div>
                    <TextInput
                        label="기본 URL"
                        size="xs"
                        autoComplete="url"
                        {...latinInputProps({inputClassName: classes.latinInput, inputMode: "url"})}
                        value={baseUrl}
                        onChange={(e) => setBaseUrl(readTextInputValue(e))}
                    />
                </div>

                <div className={classes.formTitle} style={{marginTop: 16, marginBottom: 8}}>
                    인증키
                </div>
                <div className={classes.autofillTrap} aria-hidden="true">
                    <input tabIndex={-1} type="text" name="prevent_autofill_username" autoComplete="username"/>
                    <input tabIndex={-1} type="password" name="prevent_autofill_password" autoComplete="current-password"/>
                </div>
                <div className={classes.keyRows}>
                    {keys.map((row, index) => (
                        <div key={row.id} className={classes.keyRow}>
                            <TextInput
                                label={index === 0 ? "키명" : undefined}
                                size="xs"
                                placeholder="예: client_id"
                                autoComplete="one-time-code"
                                name={`api-org-key-${row.id}`}
                                data-lpignore="true"
                                data-1p-ignore="true"
                                readOnly={!unlockedKeyFields.has(row.id)}
                                onFocus={() => unlockKeyField(row.id)}
                                {...latinInputProps({inputClassName: classes.latinInput})}
                                value={row.keyName}
                                onChange={(e) => updateKey(row.id, {keyName: readTextInputValue(e)})}
                            />
                            <TextInput
                                label={index === 0 ? "값" : undefined}
                                size="xs"
                                type="text"
                                placeholder="••••"
                                autoComplete="one-time-code"
                                name={`api-org-secret-${row.id}`}
                                data-lpignore="true"
                                data-1p-ignore="true"
                                readOnly={!unlockedKeyFields.has(row.id)}
                                onFocus={() => unlockKeyField(row.id)}
                                classNames={{input: row.showValue ? undefined : classes.secretMaskedInput}}
                                value={row.value}
                                onChange={(e) => updateKey(row.id, {value: readTextInputValue(e)})}
                                rightSection={
                                    <ActionIcon
                                        variant="subtle"
                                        color="gray"
                                        aria-label={row.showValue ? "값 숨기기" : "값 보기"}
                                        onClick={() => updateKey(row.id, {showValue: !row.showValue})}
                                    >
                                        {row.showValue ? <IconEyeOff size={14}/> : <IconEye size={14}/>}
                                    </ActionIcon>
                                }
                            />
                            <ActionIcon
                                variant="subtle"
                                color="red"
                                size="md"
                                aria-label="키 삭제"
                                onClick={() => removeKey(row.id)}
                                style={{marginBottom: 1}}
                            >
                                <IconTrash size={14}/>
                            </ActionIcon>
                        </div>
                    ))}
                </div>
                <Button size="compact-xs" variant="light" leftSection={<IconPlus size={12}/>} mt="sm" onClick={addKey}>
                    인증키 추가
                </Button>

                <div className={classes.formActions}>
                    {!isCreateMode && selectedId && (
                        <Button
                            size="xs"
                            variant="light"
                            color="red"
                            leftSection={<IconTrash size={14}/>}
                            loading={deleteOrg.isPending}
                            onClick={() => deleteOrg.mutate(selectedId)}
                        >
                            삭제
                        </Button>
                    )}
                    <Button
                        size="xs"
                        loading={registerOrg.isPending || updateOrg.isPending}
                        onClick={handleSave}
                    >
                        {isCreateMode ? "등록" : "저장"}
                    </Button>
                </div>
            </div>
        </div>
    );
}
