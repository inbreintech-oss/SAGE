import type { StateCreator } from "zustand";
import type { ToolListItem, ToolSearchQuery } from "./types";

export function parseOrTokens(raw: string): string[] {
    return raw
        .split(",")
        .map(t => t.trim().toLowerCase())
        .filter(Boolean);
}

export type SearchSliceState = {
    searchQuery: ToolSearchQuery;
};

export type SearchSliceActions = {
    setSearchRaw: (raw: string) => void;
    clearSearch: () => void;
};

export type SearchSlice = SearchSliceState & SearchSliceActions;

const initialSearch: ToolSearchQuery = { raw: "", orTokens: [] };

export const createSearchSlice: StateCreator<SearchSlice, [], [], SearchSlice> = (set) => ({
    searchQuery: initialSearch,

    setSearchRaw: (raw) =>
        set({ searchQuery: { raw, orTokens: parseOrTokens(raw) } }),

    clearSearch: () => set({ searchQuery: initialSearch }),
});

function toSearchText(value: unknown): string {
    if (value == null) return "";
    return String(value).trim();
}

export function filterToolsByQuery(
    tools: ToolListItem[],
    query: ToolSearchQuery,
): ToolListItem[] {
    if (query.orTokens.length === 0) return tools;

    return tools.filter(tool => {
        const haystack = [
            toSearchText(tool.title),
            toSearchText(tool.category),
            toSearchText(tool.keyword),
            toSearchText(tool.description),
            toSearchText(tool.tool_id),
        ]
            .join(" ")
            .toLowerCase();

        return query.orTokens.some(token => haystack.includes(token));
    });
}
