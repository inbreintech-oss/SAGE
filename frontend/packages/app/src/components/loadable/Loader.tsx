import {Center, Loader as Spinner, Stack, Text} from "@mantine/core";

/**
 * Lazy loading 페이지에 사용하는 로더 컴포넌트
 */
export default function Loader() {
    return (
        <Center style={{flex: 1, minHeight: 240, width: "100%"}}>
            <Stack align="center" gap="xs">
                <Spinner/>
                <Text size="xs" c="dimmed">페이지 로딩 중…</Text>
            </Stack>
        </Center>
    );
}
