import {Button, Modal, Stack, Text, TextInput} from "@mantine/core";

type FindPasswordModalProps = Readonly<{
    opened: boolean;
    onClose: () => void;
}>;

/** 비밀번호 찾기 Mock 모달 — API 미연동 */
export default function FindPasswordModal({opened, onClose}: FindPasswordModalProps) {
    return (
        <Modal opened={opened} onClose={onClose} title="비밀번호 찾기" centered size="sm">
            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    onClose();
                }}
            >
                <Stack gap="sm">
                    <TextInput label="이메일" type="email" placeholder="admin@sage.local" required size="sm" data-autofocus/>
                    <Text size="xs" c="dimmed">
                        Mock — 등록 이메일로 재설정 안내를 보내는 흐름을 가정합니다.
                    </Text>
                    <Button type="submit" fullWidth>
                        안내 메일 요청
                    </Button>
                </Stack>
            </form>
        </Modal>
    );
}
