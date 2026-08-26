import {Box, Group} from "@mantine/core";
import {Logo} from "@/components";
import {IconDatabaseImport} from "@tabler/icons-react";
import {APP_BRAND_BAR_HEIGHT} from "@/layouts/app/constants";

export type HeaderLogoProps = Readonly<{
    height?: number;
}>;

export default function NavLogo({
    height = APP_BRAND_BAR_HEIGHT,
}: HeaderLogoProps) {
    return (
        <Box h={height}
             style={{
                 flexShrink: 0,
                 backgroundColor: "#0F172A",
             }}
        >
            <Group w="100%" h="100%" px="lg" gap={10} wrap="nowrap">
                <IconDatabaseImport
                    size={22}
                    color="#E2E8F0"
                    style={{ flexShrink: 0 }}
                />
                <Logo color="#FFFFFF" />
            </Group>
        </Box>
    )
}
