import { modals } from "@mantine/modals";
import { Text } from "@mantine/core";
import {useTranslation} from "react-i18next";

export type ConfirmModalOptions = {
    title: string,
    message: string,
    labels?: {
        confirm?: string,
        cancel?: string
    },
    onConfirm?: () => void,
    onCancel?: () => void
}

/**
 * @mantine/modals의 기능을 간단하게 사용하기 위한 훅 입니다.
 * 더 자세한 커스터마이징이 필요하다면 @mantine/core의 Modal 컴포넌트를 사용하거나 @mantine/modals의 modals 객체를 직접 사용하세요.
 * @returns {(({title, message, labels, onConfirm, onCancel}: ConfirmModalOptions) => void)[]}
 */
export function useModals() {
    const {t} = useTranslation();

    const openConfirmModal = ({
        title,
        message,
        labels,
        onConfirm,
        onCancel
    }: ConfirmModalOptions) => {
        modals.openConfirmModal({
            title: title,
            children: (
                <Text>{message}</Text>
            ),
            labels: {
                confirm: labels?.confirm || t("common.labels.ok"),
                cancel: labels?.cancel || t("common.labels.cancel")
            },
            onConfirm: onConfirm,
            onCancel: onCancel
        });
    }

    return [
        openConfirmModal
    ];
}
