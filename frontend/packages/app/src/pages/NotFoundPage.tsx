import {DefaultAppPageLayout} from "@/layouts/appPage";
import {Title, Button, Box} from "@mantine/core";
import {useNavigate} from "react-router-dom";
import {useTranslation} from "react-i18next";

export default function NotFoundPage() {
    const {t} = useTranslation();
    const navigate = useNavigate();

    const goToHome = () => {
        navigate("/");
    };

    return (
        <DefaultAppPageLayout>
            <Title order={3}>{t("common.labels.page404-title")}</Title>
            <Box>
                <Button onClick={goToHome} mt="md">
                    {t("common.labels.return-home")}
                </Button>
            </Box>
        </DefaultAppPageLayout>
    )
}
