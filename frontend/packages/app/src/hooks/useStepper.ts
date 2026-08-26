import {useState} from "react";

export interface UseStepperProps<T> {
    steps: T[];
    initialStep?: number;
}

export function useStepper<T>({steps, initialStep = 0}: UseStepperProps<T>) {
    const [currentStep, setCurrentStep] = useState(initialStep);

    const next = () => setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
    const prev = () => setCurrentStep((prev) => Math.max(prev - 1, 0));
    const setStep = (step: number) => setCurrentStep(Math.max(0, Math.min(step, steps.length - 1)));

    return {
        currentStep,
        setStep,
        next,
        prev,
        steps,
        isFirst: currentStep === 0,
        isLast: currentStep === steps.length - 1,
    };
}
