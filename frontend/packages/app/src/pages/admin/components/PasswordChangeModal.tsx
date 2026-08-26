import {useState} from "react";
import {Button, Modal, Stack, Text, TextInput} from "@mantine/core";
import {notifications} from "@mantine/notifications";
import {useAdminChangePassword} from "@/features/admin-settings";

type PasswordChangeModalProps = Readonly<{
    opened: boolean;
    onClose: () => void;
}>;

export default function PasswordChangeModal({opened, onClose}: PasswordChangeModalProps) {
    const changePassword = useAdminChangePassword();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const reset = () => {
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
    };

    return (
        <Modal
            opened={opened}
            onClose={() => {
                reset();
                onClose();
            }}
            title="암호 변경"
            centered
            size="sm"
        >
            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    if (newPassword !== confirmPassword) {
                        notifications.show({color: "red", message: "새 비밀번호 확인이 일치하지 않습니다."});
                        return;
                    }
                    changePassword.mutate(
                        {currentPassword, newPassword},
                        {
                            onSuccess: () => {
                                notifications.show({color: "teal", message: "비밀번호가 변경되었습니다."});
                                reset();
                                onClose();
                            },
                            onError: (error) => {
                                notifications.show({
                                    color: "red",
                                    title: "변경 실패",
                                    message: error instanceof Error ? error.message : "비밀번호 변경에 실패했습니다.",
                                });
                            },
                        },
                    );
                }}
            >
                <Stack gap="sm">
                    <TextInput
                        label="현재 비밀번호"
                        type="password"
                        required
                        size="sm"
                        autoComplete="current-password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.currentTarget.value)}
                        data-autofocus
                    />
                    <TextInput
                        label="새 비밀번호"
                        type="password"
                        required
                        size="sm"
                        autoComplete="new-password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.currentTarget.value)}
                    />
                    <TextInput
                        label="새 비밀번호 확인"
                        type="password"
                        required
                        size="sm"
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.currentTarget.value)}
                    />
                    <Button type="submit" fullWidth loading={changePassword.isPending}>
                        변경
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
