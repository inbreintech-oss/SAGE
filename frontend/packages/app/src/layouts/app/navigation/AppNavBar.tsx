import {useMenu} from "@/hooks";
import {ScrollArea} from "@mantine/core";
import {AppNav} from "@/components";

type AppNavBarProps = Readonly<{
    /** Icon Rail 접힘 — 아이콘만 표시 */
    compact?: boolean;
}>;

export default function AppNavBar({compact = false}: AppNavBarProps) {
    const {currentMenu, menus, isMenuLoading} = useMenu();

    return (
        <ScrollArea
            flex={1}
            w="100%"
            type="hover"
            style={{minHeight: 0}}
            scrollbarSize={4}
            styles={{
                scrollbar: {
                    borderTop: "none",
                    background: "transparent",
                },
                thumb: {
                    background: "var(--sage-border-color)",
                },
            }}
        >
            <AppNav
                menus={menus}
                currentMenu={currentMenu}
                isLoading={isMenuLoading}
                compact={compact}
            />
        </ScrollArea>
    );
}
