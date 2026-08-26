import type { StateCreator } from "zustand";
import type { DmColumn, DmFileNode, DmSheet } from "./types";
import { cloneFileNode } from "./types";

export type FileHierarchyState = {
    currentFile: DmFileNode | null;
    /** UI 표시용 로컬 File 객체 (업로드 전 파일명 표기) */
    localFile: File | null;
};

export type FileHierarchyActions = {
    setUploadedFile: (node: DmFileNode, localFile: File) => void;
    clearFile: () => void;
    setActiveSheet: (sheetId: string) => void;
    setActiveSheetByName: (sheetName: string) => void;
    toggleColumn: (sheetId: string, columnId: string) => void;
    toggleColumnByIndex: (sheetName: string, colIdx: number) => void;
    restoreFileFromPool: (node: DmFileNode) => void;
};

export const createFileHierarchySlice: StateCreator<
    FileHierarchyState & FileHierarchyActions,
    [],
    [],
    FileHierarchyState & FileHierarchyActions
> = (set, get) => ({
    currentFile: null,
    localFile: null,

    setUploadedFile: (node, localFile) =>
        set({ currentFile: node, localFile }),

    clearFile: () =>
        set({ currentFile: null, localFile: null }),

    setActiveSheet: (sheetId) =>
        set(s => {
            if (!s.currentFile) return s;
            return { currentFile: { ...s.currentFile, activeSheetId: sheetId } };
        }),

    setActiveSheetByName: (sheetName) => {
        const file = get().currentFile;
        if (!file) return;
        const sheet = file.sheets.find(s => s.name === sheetName);
        if (sheet) get().setActiveSheet(sheet.id);
    },

    toggleColumn: (sheetId, columnId) =>
        set(s => {
            const file = s.currentFile;
            if (!file) return s;
            return {
                currentFile: {
                    ...file,
                    sheets: file.sheets.map((sheet): DmSheet =>
                        sheet.id !== sheetId
                            ? sheet
                            : {
                                  ...sheet,
                                  columns: sheet.columns.map((col): DmColumn =>
                                      col.id !== columnId
                                          ? col
                                          : { ...col, selected: !col.selected }
                                  ),
                              }
                    ),
                },
            };
        }),

    toggleColumnByIndex: (sheetName, colIdx) => {
        const file = get().currentFile;
        if (!file) return;
        const sheet = file.sheets.find(s => s.name === sheetName);
        const col = sheet?.columns[colIdx];
        if (sheet && col) get().toggleColumn(sheet.id, col.id);
    },

    restoreFileFromPool: (node) =>
        set({ currentFile: cloneFileNode(node), localFile: null }),
});

export const selectActiveSheet = (s: FileHierarchyState): DmSheet | null => {
    const f = s.currentFile;
    if (!f?.activeSheetId) return null;
    return f.sheets.find(sh => sh.id === f.activeSheetId) ?? null;
};

export const selectSheetNames = (s: FileHierarchyState): string[] =>
    s.currentFile?.sheets.map(sh => sh.name) ?? [];

export const selectActiveColumns = (s: FileHierarchyState): { name: string; type: string }[] => {
    const sheet = selectActiveSheet(s);
    return (sheet?.columns ?? []).map(c => ({ name: c.name, type: c.dtype }));
};

export const selectSheetColumnMap = (s: FileHierarchyState): Record<string, boolean[]> => {
    const file = s.currentFile;
    if (!file) return {};
    return Object.fromEntries(
        file.sheets.map(sh => [sh.name, sh.columns.map(c => c.selected)])
    );
};
