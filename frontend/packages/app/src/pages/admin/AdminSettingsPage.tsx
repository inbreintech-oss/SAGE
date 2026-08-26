import {useState} from "react";
import {Paper, SegmentedControl, Stack, Title} from "@mantine/core";
import {IconSettings} from "@tabler/icons-react";
import {DefaultAppPageLayout} from "@/layouts/appPage";
import UsersPanel from "./components/UsersPanel";
import CategoryPanel from "./components/CategoryPanel";
import ApiOrgPanel from "./components/ApiOrgPanel";
import {PanelErrorBoundary} from "./components/PanelErrorBoundary";
import classes from "./adminSettings.module.css";

type SettingsTab = "users" | "categories" | "apiOrgs";

/**
 * 시스템 설정 — SAGE.py /admin API 연동
 */
export default function AdminSettingsPage() {
    const [tab, setTab] = useState<SettingsTab>("users");

    return (
        <DefaultAppPageLayout icon={<IconSettings size={22}/>} title="시스템 설정">
            <div className={classes.page}>
                <Paper className={classes.panel} withBorder radius="md" p="lg" shadow="xs">
                    <div className={classes.panelHeader}>
                        <Title order={3} className={classes.panelTitle}>
                            시스템 설정
                        </Title>
                    </div>

                    <div className={classes.segmentWrap}>
                        <SegmentedControl
                            fullWidth
                            size="sm"
                            value={tab}
                            onChange={(v) => setTab(v as SettingsTab)}
                            data={[
                                {label: "사용자", value: "users"},
                                {label: "공통코드", value: "categories"},
                                {label: "API 연계 기관", value: "apiOrgs"},
                            ]}
                        />
                    </div>

                    <Stack gap="md">
                        <PanelErrorBoundary label="설정 탭">
                            {tab === "users" && <UsersPanel/>}
                            {tab === "categories" && <CategoryPanel/>}
                            {tab === "apiOrgs" && <ApiOrgPanel/>}
                        </PanelErrorBoundary>
                    </Stack>
                </Paper>
            </div>
        </DefaultAppPageLayout>
    );
}
