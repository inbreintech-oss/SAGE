import type {IUserInfo} from "@/libs/types";
import AppAvatarButton from "@/components/appAvatar/AppAvatarButton";

export type AppAvatarProps = Readonly<{
    user?: IUserInfo | null,
    onEvent?: (e: AppAvatarActions) => void;
}>;

export type AppAvatarActions = "logout" | "settings";

// User Avatar Control
export default function AppAvatar({
    user
}: AppAvatarProps) {

    return (
        <AppAvatarButton user={user}/>
    )
}
