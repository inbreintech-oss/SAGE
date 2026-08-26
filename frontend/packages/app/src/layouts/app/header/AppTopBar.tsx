import {useState} from "react";
import {
    ActionIcon,
    Menu,
    TextInput,
    Tooltip,
    useMantineColorScheme,
} from "@mantine/core";
import {
    IconBell,
    IconDatabase,
    IconKey,
    IconLogout,
    IconLogin,
    IconMoon,
    IconSearch,
    IconSettings,
    IconSun,
    IconUser,
} from "@tabler/icons-react";
import {useNavigate} from "react-router-dom";
import {notifications} from "@mantine/notifications";
import classes from "./AppTopBar.module.css";
import {useAdminAuth, useAdminLogin, useAdminLogout} from "@/features/admin-settings";
import LoginModal from "@/pages/admin/components/LoginModal";
import PasswordChangeModal from "@/pages/admin/components/PasswordChangeModal";
import FindPasswordModal from "@/pages/admin/components/FindPasswordModal";

export default function AppTopBar() {
    const {colorScheme, setColorScheme} = useMantineColorScheme();
    const isDark = colorScheme === "dark";
    const navigate = useNavigate();

    const authQuery = useAdminAuth();
    const loginMutation = useAdminLogin();
    const logoutMutation = useAdminLogout();

    const auth = authQuery.data;
    const loggedIn = auth?.loggedIn ?? false;
    const user = auth?.user ?? null;

    const [loginOpen, setLoginOpen] = useState(false);
    const [passwordOpen, setPasswordOpen] = useState(false);
    const [findPasswordOpen, setFindPasswordOpen] = useState(false);

    const handleLogin = async (loginId: string, password: string) => {
        try {
            await loginMutation.mutateAsync({loginId, password});
            setLoginOpen(false);
            notifications.show({color: "teal", message: "로그인되었습니다."});
        } catch (error) {
            notifications.show({
                color: "red",
                title: "로그인 실패",
                message: error instanceof Error ? error.message : "ID 또는 비밀번호를 확인하세요.",
            });
        }
    };

    const handleLogout = async () => {
        try {
            await logoutMutation.mutateAsync();
            navigate("/");
        } catch {
            navigate("/");
        }
    };

    return (
        <>
            <header className={classes.root}>
                <div className={classes.left}>
                    <IconDatabase size={20} color="var(--sage-brand-primary)"/>
                    <span className={classes.brand}>SAG-E</span>
                </div>

                <div className={classes.searchCenter}>
                    <TextInput
                        className={classes.searchWrap}
                        placeholder="모델, 보고서, 도구 검색..."
                        leftSection={<IconSearch size={16} color="var(--sage-topbar-icon, #71717a)"/>}
                        size="xs"
                        radius="md"
                        styles={{
                            input: {
                                background: "var(--sage-topbar-search-bg)",
                                border: "none",
                                color: "var(--sage-topbar-text)",
                            },
                        }}
                    />
                </div>

                <div className={classes.right}>
                    <Tooltip label={isDark ? "라이트 모드" : "다크 모드"}>
                        <ActionIcon
                            variant="subtle"
                            size="md"
                            className={classes.iconBtn}
                            aria-label="테마 전환"
                            onClick={() => setColorScheme(isDark ? "light" : "dark")}
                        >
                            {isDark ? <IconSun size={18}/> : <IconMoon size={18}/>}
                        </ActionIcon>
                    </Tooltip>
                    <ActionIcon variant="subtle" size="md" className={classes.iconBtn} aria-label="알림">
                        <IconBell size={18}/>
                    </ActionIcon>

                    <Menu shadow="md" width={180} position="bottom-end" withinPortal>
                        <Menu.Target>
                            <ActionIcon
                                variant="subtle"
                                size="md"
                                className={classes.iconBtn}
                                aria-label="관리자 메뉴"
                            >
                                <IconUser size={18}/>
                            </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                            {loggedIn && user ? (
                                <>
                                    <Menu.Label>{user.name || user.login_id}</Menu.Label>
                                    <Menu.Item
                                        leftSection={<IconLogout size={14}/>}
                                        onClick={handleLogout}
                                    >
                                        로그아웃
                                    </Menu.Item>
                                    <Menu.Item
                                        leftSection={<IconKey size={14}/>}
                                        onClick={() => setPasswordOpen(true)}
                                    >
                                        암호변경
                                    </Menu.Item>
                                    <Menu.Item
                                        leftSection={<IconSettings size={14}/>}
                                        onClick={() => navigate("/admin/settings")}
                                    >
                                        설정
                                    </Menu.Item>
                                </>
                            ) : (
                                <Menu.Item
                                    leftSection={<IconLogin size={14}/>}
                                    onClick={() => setLoginOpen(true)}
                                >
                                    로그인
                                </Menu.Item>
                            )}
                        </Menu.Dropdown>
                    </Menu>
                </div>
            </header>

            <LoginModal
                opened={loginOpen}
                onClose={() => setLoginOpen(false)}
                onSubmit={handleLogin}
                loading={loginMutation.isPending}
                onFindPassword={() => {
                    setLoginOpen(false);
                    setFindPasswordOpen(true);
                }}
            />
            <PasswordChangeModal opened={passwordOpen} onClose={() => setPasswordOpen(false)}/>
            <FindPasswordModal opened={findPasswordOpen} onClose={() => setFindPasswordOpen(false)}/>
        </>
    );
}
