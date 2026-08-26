import type {ChangeEvent} from "react";

/** Mantine TextInput onChange — string 또는 native event 모두 처리 */
export function readTextInputValue(value: string | ChangeEvent<HTMLInputElement>): string {
    if (typeof value === "string") return value;
    const target = value.target as HTMLInputElement | null;
    return target?.value ?? value.currentTarget?.value ?? "";
}

type LatinInputOptions = {
    inputClassName?: string;
    inputMode?: "latin" | "url" | "email";
};

/** 코드·ID 등 — IME 영문(라틴) 입력 기본 */
export function latinInputProps({inputClassName, inputMode = "latin"}: LatinInputOptions = {}) {
    return {
        lang: "en",
        inputMode,
        spellCheck: false,
        autoCapitalize: "off" as const,
        autoCorrect: "off" as const,
        ...(inputClassName ? {classNames: {input: inputClassName} as const} : {}),
    };
}
