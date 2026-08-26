import {Button, Modal, Stack, Text, TextInput} from "@mantine/core";

type LoginModalProps = Readonly<{
    opened: boolean;
    onClose: () => void;
    onSubmit: (loginId: string, password: string) => void | Promise<void>;
    loading?: boolean;
    onFindPassword: () => void;
}>;

export default function LoginModal({
    opened,
    onClose,
    onSubmit,
    loading,
    onFindPassword,
}: LoginModalProps) {
    return (
        <Modal opened={opened} onClose={onClose} title="관리자 로그인" centered size="sm">
            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    const fd = new FormData(e.currentTarget);
                    void onSubmit(String(fd.get("loginId") ?? ""), String(fd.get("password") ?? ""));
                }}
            >
                <Stack gap="sm">
                    <TextInput
                        name="loginId"
                        label="ID"
                        placeholder="admin"
                        required
                        size="sm"
                        autoComplete="username"
                        data-autofocus
                    />
                    <TextInput
                        name="password"
                        label="Password"
                        type="password"
                        placeholder="••••••••"
                        required
                        size="sm"
                        autoComplete="current-password"
                    />
                    <Text size="xs" c="dimmed">
                        SAGE.py 관리 계정으로 로그인합니다. (기본: admin / admin — 시드 후 변경 권장)
                    </Text>
                    <Button type="submit" fullWidth loading={loading}>
                        로그인
                    </Button>
                    <Button type="button" variant="subtle" size="compact-xs" onClick={onFindPassword}>
                        비밀번호 찾기
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
