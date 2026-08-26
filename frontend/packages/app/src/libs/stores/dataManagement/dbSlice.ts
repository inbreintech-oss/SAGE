import type { StateCreator } from "zustand";
import {
    sanitizeDbIdentifier,
    sanitizeDbPassword,
    sanitizeDbUsername,
    sanitizeHost,
    sanitizePort,
    sanitizeSqlQuery,
} from "./dbValidators";
import {
    DB_VENDOR_DEFAULT_PORTS,
    EMPTY_DB_FORM,
    type DbColumnMeta,
    type DbForm,
    type DbPoolSeal,
    type DbVendor,
} from "./types";

export type DbConnStatus = "idle" | "connecting" | "success" | "error";

export type DbSliceState = {
    dbForm: DbForm;
    isDbLocked: boolean;
    dbColumns: DbColumnMeta[];
    connStatus: DbConnStatus;
    isConnecting: boolean;
};

export type DbSliceActions = {
    setDbForm: (form: DbForm) => void;
    updateDbField: (key: keyof DbForm, value: string) => void;
    setDbVendor: (vendor: DbVendor) => void;
    setDbColumns: (columns: DbColumnMeta[]) => void;
    toggleDbColumn: (index: number) => void;
    setConnStatus: (status: DbConnStatus) => void;
    setIsConnecting: (v: boolean) => void;
    lockDbForm: (seal: DbPoolSeal) => void;
    unlockDbForm: () => void;
    restoreDbFromPool: (seal: DbPoolSeal) => void;
    clearDb: () => void;
};

export const createDbSlice: StateCreator<
    DbSliceState & DbSliceActions,
    [],
    [],
    DbSliceState & DbSliceActions
> = (set) => ({
    dbForm: { ...EMPTY_DB_FORM },
    isDbLocked: false,
    dbColumns: [],
    connStatus: "idle",
    isConnecting: false,

    setDbForm: (form) => set({ dbForm: form }),

    updateDbField: (key, value) =>
        set(s => {
            if (s.isDbLocked) return s;
            let sanitized = value;
            switch (key) {
                case "host": sanitized = sanitizeHost(value); break;
                case "port": sanitized = sanitizePort(value); break;
                case "dbName":
                case "tableName": sanitized = sanitizeDbIdentifier(value); break;
                case "username": sanitized = sanitizeDbUsername(value); break;
                case "password": sanitized = sanitizeDbPassword(value); break;
                case "query": sanitized = sanitizeSqlQuery(value); break;
            }
            return {
                dbForm: { ...s.dbForm, [key]: sanitized },
                connStatus: key !== "query" ? "idle" : s.connStatus,
                dbColumns: key !== "query" ? [] : s.dbColumns,
            };
        }),

    setDbVendor: (vendor) =>
        set(s => {
            if (s.isDbLocked) return s;
            const prevDefault = DB_VENDOR_DEFAULT_PORTS[s.dbForm.vendor];
            const nextPort = s.dbForm.port === prevDefault || !s.dbForm.port
                ? DB_VENDOR_DEFAULT_PORTS[vendor]
                : s.dbForm.port;
            return {
                dbForm: { ...s.dbForm, vendor, port: nextPort },
                connStatus: "idle",
                dbColumns: [],
            };
        }),

    setDbColumns: (columns) => set({ dbColumns: columns }),

    toggleDbColumn: (index) =>
        set(s => ({
            dbColumns: s.dbColumns.map((col, i) =>
                i === index ? { ...col, selected: !col.selected } : col
            ),
        })),

    setConnStatus: (status) => set({ connStatus: status }),

    setIsConnecting: (v) => set({ isConnecting: v }),

    lockDbForm: (seal) => {
        const { columns, ...form } = seal;
        set({
            dbForm: form,
            dbColumns: columns.map(c => ({ ...c })),
            isDbLocked: true,
            connStatus: columns.length > 0 ? "success" : "idle",
            isConnecting: false,
        });
    },

    unlockDbForm: () => set({ isDbLocked: false }),

    restoreDbFromPool: (seal) => {
        const { columns, ...form } = seal;
        set({
            dbForm: { ...form },
            dbColumns: columns.map(c => ({ ...c })),
            isDbLocked: false,
            connStatus: columns.length > 0 ? "success" : "idle",
            isConnecting: false,
        });
    },

    clearDb: () =>
        set({
            dbForm: { ...EMPTY_DB_FORM },
            isDbLocked: false,
            dbColumns: [],
            connStatus: "idle",
            isConnecting: false,
        }),
});
