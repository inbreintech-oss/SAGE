import {type MantineColor, type StyleProp, Title, type TitleOrder} from "@mantine/core";

type LogoProps = Readonly<{
    size?: "sm" | "md" | "lg",
    color?: StyleProp<MantineColor>;
}>

export default function Logo({
    size = "md",
    color,
}: LogoProps) {
    let order: TitleOrder = 1;
    switch (size) {
        case "sm":
            order = 4;
            break;
        default:
        case "md":
            order = 3;
            break;
        case "lg":
            order = 1;
            break;
    }

    return (
        <Title order={order} c={color}>SAG-E Analytics</Title>
    )
}