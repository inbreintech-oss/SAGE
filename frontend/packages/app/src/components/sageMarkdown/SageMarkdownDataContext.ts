import { createContext, useContext } from "react";

export type SageMarkdownDataItem = {
    type: string;
    value: unknown;
}

export type SageMarkdownData = Record<string, SageMarkdownDataItem>;

export const SageMarkdownDataContext = createContext<SageMarkdownData>({});

export function useSageMarkdownData(): SageMarkdownData {
    return useContext(SageMarkdownDataContext);
}
