import {useState} from "react";
import {
    ActionIcon,
    Badge,
    Button,
    Loader,
    SegmentedControl,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import {useMutation, useQueryClient} from "@tanstack/react-query";
import {notifications} from "@mantine/notifications";
import {IconEye, IconEyeOff, IconPlus, IconTrash} from "@tabler/icons-react";
import {
    adminKeys,
    adminMutations,
    checkEmailAvailable,
    checkLoginIdAvailable,
    useAdminUsers,
} from "@/features/admin-settings";
import type {AdminUser, AdminUserRole} from "@/features/admin-settings";
import {readTextInputValue, latinInputProps} from "./inputHelpers";
import classes from "../adminSettings.module.css";

const emptyForm = {
    name: "",
    loginId: "",
    password: "",
    email: "",
    type: "admin" as AdminUserRole,
};

export default function UsersPanel() {
    const qc = useQueryClient();
    const usersQuery = useAdminUsers();
    const users = usersQuery.data ?? [];

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [form, setForm] = useState(emptyForm);
    const [mode, setMode] = useState<"create" | "edit">("create");
    const [showPassword, setShowPassword] = useState(false);
    const [validating, setValidating] = useState(false);

    const invalidate = () => qc.invalidateQueries({queryKey: adminKeys.users()});

    const onError = (error: Error) => {
        notifications.show({
            color: "red",
            title: "사용자 처리 실패",
            message: error.message || "요청 처리 중 오류가 발생했습니다.",
        });
    };

    const registerUser = useMutation({
        ...adminMutations.registerUser(),
        onSuccess: () => {
            invalidate();
            setForm(emptyForm);
            setMode("create");
            setSelectedId(null);
            setShowPassword(false);
            notifications.show({color: "teal", message: "사용자가 등록되었습니다."});
        },
        onError,
    });

    const updateUser = useMutation({
        ...adminMutations.updateUser(),
        onSuccess: () => {
            invalidate();
            notifications.show({color: "teal", message: "사용자 정보가 저장되었습니다."});
        },
        onError,
    });

    const deleteUser = useMutation({
        ...adminMutations.deleteUser(),
        onSuccess: () => {
            invalidate();
            setForm(emptyForm);
            setMode("create");
            setSelectedId(null);
            notifications.show({color: "teal", message: "사용자가 삭제되었습니다."});
        },
        onError,
    });

    const selectUser = (user: AdminUser) => {
        setSelectedId(user.user_id);
        setMode("edit");
        setShowPassword(false);
        setForm({
            name: user.name,
            loginId: user.login_id,
            password: "",
            email: user.email,
            type: user.role,
        });
    };

    const startCreate = () => {
        setSelectedId(null);
        setMode("create");
        setShowPassword(false);
        setForm(emptyForm);
    };

    const handleSubmit = async () => {
        if (mode === "create") {
            const loginId = form.loginId.trim();
            const email = form.email.trim();

            if (!loginId) {
                notifications.show({color: "red", message: "ID를 입력해 주세요."});
                return;
            }
            if (!form.password) {
                notifications.show({color: "red", message: "Password를 입력해 주세요."});
                return;
            }

            setValidating(true);
            try {
                const idAvailable = await checkLoginIdAvailable(loginId);
                if (!idAvailable) {
                    notifications.show({color: "red", message: "이미 사용 중인 ID입니다."});
                    return;
                }
                if (email) {
                    const emailAvailable = await checkEmailAvailable(email);
                    if (!emailAvailable) {
                        notifications.show({color: "red", message: "이미 사용 중인 이메일입니다."});
                        return;
                    }
                }
            } catch (error) {
                onError(error instanceof Error ? error : new Error("중복 확인에 실패했습니다."));
                return;
            } finally {
                setValidating(false);
            }

            registerUser.mutate({
                login_id: loginId,
                name: form.name.trim(),
                email,
                password: form.password,
                role: form.type,
            });
            return;
        }

        if (selectedId) {
            const email = form.email.trim();
            if (email) {
                setValidating(true);
                try {
                    const emailAvailable = await checkEmailAvailable(email, selectedId);
                    if (!emailAvailable) {
                        notifications.show({color: "red", message: "이미 사용 중인 이메일입니다."});
                        return;
                    }
                } catch (error) {
                    onError(error instanceof Error ? error : new Error("중복 확인에 실패했습니다."));
                    return;
                } finally {
                    setValidating(false);
                }
            }

            updateUser.mutate({
                user_id: selectedId,
                name: form.name.trim(),
                email,
                password: form.password || null,
                role: form.type,
            });
        }
    };

    if (usersQuery.isLoading) {
        return <div className={classes.emptyState}><Loader size="sm"/></div>;
    }

    if (usersQuery.isError) {
        return (
            <div className={classes.emptyState}>
                사용자 목록을 불러오지 못했습니다. 로그인 상태와 SAGE.py 서버를 확인하세요.
            </div>
        );
    }

    return (
        <div className={classes.section}>
            <div className={classes.codePanel}>
                <div className={classes.codePanelTitleRow}>
                    <span className={classes.codePanelTitle}>등록 사용자</span>
                    <span className={classes.codePanelMeta}>{users.length}명</span>
                </div>
                <div className={`${classes.codePanelBody} ${classes.codeListFixed}`}>
                    {users.length === 0 ? (
                        <div className={classes.codeListEmpty}>등록된 사용자가 없습니다.</div>
                    ) : (
                        <table className={classes.table}>
                            <thead>
                                <tr>
                                    <th>사용자명</th>
                                    <th>ID</th>
                                    <th>이메일</th>
                                    <th>유형</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((user) => (
                                    <tr
                                        key={user.user_id}
                                        data-clickable
                                        data-selected={selectedId === user.user_id || undefined}
                                        onClick={() => selectUser(user)}
                                    >
                                        <td>{user.name}</td>
                                        <td>{user.login_id}</td>
                                        <td>{user.email}</td>
                                        <td>
                                            <Badge size="xs" variant="light" color={user.role === "admin" ? "teal" : "gray"}>
                                                {user.role === "admin" ? "관리자" : "일반"}
                                            </Badge>
                                        </td>
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
                        {mode === "create" ? "사용자 등록" : "사용자 수정"}
                    </div>
                    <Button size="compact-xs" variant="light" leftSection={<IconPlus size={12}/>} onClick={startCreate}>
                        신규
                    </Button>
                </div>
                <Stack gap="sm">
                    <div className={classes.formRowTwoCol}>
                        <TextInput
                            label="사용자명"
                            size="xs"
                            autoComplete="off"
                            value={form.name}
                            onChange={(e) => setForm((f) => ({...f, name: readTextInputValue(e)}))}
                        />
                        <TextInput
                            label={mode === "create" ? "비밀번호" : "비밀번호 (변경 시 입력)"}
                            size="xs"
                            type={showPassword ? "text" : "password"}
                            autoComplete="new-password"
                            value={form.password}
                            onChange={(e) => setForm((f) => ({...f, password: readTextInputValue(e)}))}
                            rightSection={
                                <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    aria-label={showPassword ? "암호 숨기기" : "암호 보기"}
                                    onClick={() => setShowPassword((v) => !v)}
                                >
                                    {showPassword ? <IconEyeOff size={14}/> : <IconEye size={14}/>}
                                </ActionIcon>
                            }
                        />
                    </div>
                    <div className={classes.formRowTwoCol}>
                        <TextInput
                            label="ID"
                            size="xs"
                            autoComplete="off"
                            {...latinInputProps({inputClassName: classes.latinInput})}
                            value={form.loginId}
                            disabled={mode === "edit"}
                            onChange={(e) => setForm((f) => ({...f, loginId: readTextInputValue(e)}))}
                        />
                        <TextInput
                            label="이메일"
                            size="xs"
                            autoComplete="email"
                            {...latinInputProps({inputClassName: classes.latinInput, inputMode: "email"})}
                            value={form.email}
                            onChange={(e) => setForm((f) => ({...f, email: readTextInputValue(e)}))}
                        />
                    </div>
                </Stack>
                <Stack gap={6} mt="sm">
                    <Text size="xs" fw={500}>유형</Text>
                    <SegmentedControl
                        size="xs"
                        value={form.type}
                        onChange={(v) => setForm((f) => ({...f, type: v as AdminUserRole}))}
                        data={[
                            {label: "관리자", value: "admin"},
                            {label: "일반", value: "member"},
                        ]}
                    />
                </Stack>
                <div className={classes.formActions}>
                    {mode === "edit" && selectedId && (
                        <Button
                            size="xs"
                            variant="light"
                            color="red"
                            leftSection={<IconTrash size={14}/>}
                            loading={deleteUser.isPending}
                            onClick={() => deleteUser.mutate(selectedId)}
                        >
                            삭제
                        </Button>
                    )}
                    <Button
                        size="xs"
                        loading={registerUser.isPending || updateUser.isPending || validating}
                        onClick={() => void handleSubmit()}
                    >
                        {mode === "create" ? "등록" : "저장"}
                    </Button>
                </div>
            </div>
        </div>
    );
}
