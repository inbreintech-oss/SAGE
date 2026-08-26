import React from "react";
import type {DefaultMantineColor} from "@mantine/core";
import {type NotificationData, notifications} from "@mantine/notifications";
import {IconCheck, IconInfoCircle, IconAlertTriangle, IconExclamationCircle} from "@tabler/icons-react";
import {useTranslation} from "react-i18next";

export type NotificationTypes = "success" | "info" | "warning" | "error";
export type NotificationsOptions = {
    type: NotificationTypes;
    message: string;
} & Omit<NotificationData, "message" | "color" | "icon">;
export type QuickNotificationOptions = Omit<NotificationsOptions, "type" | "message"> & {
    params?: Record<string, string>;
};

export function useNotifications() {
    const {show, ...rest} = notifications;
    const {t} = useTranslation();

    const showNotification = ({type, message, ...rest}: NotificationsOptions) => {
        let icon: React.ReactNode;
        let color: DefaultMantineColor;

        switch (type) {
            case "success":
                icon = <IconCheck/>;
                color = "green";
                break;
            default:
            case "info":
                icon = <IconInfoCircle/>;
                color = "blue";
                break;
            case "warning":
                icon = <IconAlertTriangle/>;
                color = "orange";
                break;
            case "error":
                icon = <IconExclamationCircle/>;
                color = "red";
                break;
        }

        show({
            icon: icon,
            color: color,
            message: message,
            autoClose: 2000,
            ...rest
        });
    }

    const quickNotificationFactory = (
        type: NotificationTypes,
        show: ((options: NotificationsOptions) => void),
    ) => (message: string, options?: QuickNotificationOptions) => {
        const {params, ...rest} = options || {};
        show({
            type: type,
            message: t(message, params),
            ...rest
        })
    }

    return {
        show: showNotification,
        showError: quickNotificationFactory("error", showNotification),
        showInfo: quickNotificationFactory("info", showNotification),
        showSuccess: quickNotificationFactory("success", showNotification),
        showWarning: quickNotificationFactory("warning", showNotification),
        ...rest
    }
}
