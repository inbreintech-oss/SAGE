export function buildFilePoolId(fileId: string, activeSheetId: string | null): string {
    return `file::${fileId}::${activeSheetId ?? "none"}`;
}
