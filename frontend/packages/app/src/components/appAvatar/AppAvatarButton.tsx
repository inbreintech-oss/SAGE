import type { IUserInfo } from "@/libs/types";
import classes from "./AppAvatarButton.module.css";
import {Avatar, Button, type ButtonProps, Center, Text} from "@mantine/core";


export type AppAvatarButtonType = Readonly<{
    user?: IUserInfo | null;
} & Omit<ButtonProps, "size" | "radius" | "variant" | "color" | "justify" | "rightSection" | "leftSection">>

export default function AppAvatarButton({
    user,
    ...buttonProps
}: AppAvatarButtonType) {
    return (
        <Button {...buttonProps}
                classNames={classes}
                size="compact-md"
                radius="lg"
                variant="transparent"
                pr={0}
                justify="space-between"
                rightSection={<Avatar size="2em" variant="transparent" color="blue"/>}>
            <Center w="100%" h="100%" visibleFrom="sm">
                <Text size="sm">
                    {user?.lastName}&nbsp;{user?.firstName}
                </Text>
            </Center>
        </Button>
    )
}
