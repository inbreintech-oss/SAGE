import React from "react";
import {Group, Text} from "@mantine/core";

export type AppStepperProps = {
    currentStep: number;
    children: React.ReactNode;
}

export type AppStepProps = {
    step?: number;
    children: React.ReactNode;
}

export function AppStep({children}: AppStepProps) {
    return <>{children}</>;
}

export default function AppStepper({
    currentStep,
    children
}: AppStepperProps) {
    const steps = React.Children.toArray(children);

    return (
        <Group gap="md">
            {steps.map((step, index) => {
                const isActive = index === currentStep;

                return (
                    <Text key={index}
                          component="span"
                          size="md"
                          fw="bold"
                          style={{
                              color: isActive ? "#333333" : "#7F7F7F",
                              transition: 'all 0.2s ease',
                              display: 'inline-block'
                          }}
                    >
                        {step}
                    </Text>
                );
            })}
        </Group>
    );
}

AppStepper.Step = AppStep;