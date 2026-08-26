import React from "react";

export type FilterBaseProps = {
    ref?: React.RefObject<HTMLInputElement | null>;
    value?: any;
    onSubmit?: (value: any) => void;
    onDismiss?: () => void;
    onReset?: () => void;
}
