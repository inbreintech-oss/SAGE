import React from "react";
import {AppHeader} from "@/layouts/app";
import {AppStepper, type AppHeaderButtonProps} from "@/components";

type DefaultAppPageLayout = Readonly<{
    children?: React.ReactNode;
    buttons?: React.ReactNode | AppHeaderButtonProps[];
    icon?: React.ReactNode;
    title?: string;
    steps?: string[];
    currentStep?: number;
}>;

export function DefaultAppPageLayout({
    children,
    steps,
    currentStep,
    buttons,
    icon,
    title,
}: DefaultAppPageLayout) {

    const renderStepper = (step: number, stepLabels: string[]) => {
        return (
            <AppStepper currentStep={step}>
                {stepLabels.map((stepLabel, index) => (
                    <AppStepper.Step key={index}>
                        {stepLabel}
                    </AppStepper.Step>
                ))}
            </AppStepper>
        );
    };

    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                flex: 1,
                minHeight: 0,
                width: "100%",
                overflow: "hidden",
            }}
        >
            <AppHeader
                stepperArea={(steps && currentStep != undefined) && renderStepper(currentStep, steps)}
                buttonsArea={buttons}
                icon={icon}
                title={title}
            />
            <div
                style={{
                    flex: 1,
                    minHeight: 0,
                    overflowY: "auto",
                    overflowX: "hidden",
                    padding: "var(--mantine-spacing-md)",
                }}
            >
                {children}
            </div>
        </div>
    );
}
