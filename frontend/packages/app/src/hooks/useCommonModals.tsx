import {modals} from "@mantine/modals";
import {Text} from "@mantine/core";
import {useTranslation} from "react-i18next";

export type openConfirmModalOptions = {
    title: string;
    content: string;
    onConfirm?: () => void;
    onCancel?: () => void;
    onAbort?: () => void;
    onBlur?: () => void;
    onClose?: () => void;
    closeOnClickOutside?: boolean;
}

export function useCommonModals() {
    const {t} = useTranslation();

    const openConfirmModal = ({
        title,
        content,
        onConfirm,
        onCancel,
        onAbort,
        onBlur,
        onClose,
        closeOnClickOutside
    }: openConfirmModalOptions) => {
        modals.openConfirmModal({
            title,
            children: (
                <Text size={"sm"}>
                    {content}
                </Text>
            ),
            labels: {
                confirm: t("common.labels.confirm"),
                cancel: t("common.labels.cancel"),
            },
            onConfirm,
            onCancel,
            onAbort,
            onBlur,
            onClose,
            closeOnClickOutside
        });
    }

    return {
        openConfirmModal
    }
}
