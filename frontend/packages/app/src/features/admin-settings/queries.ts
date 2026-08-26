import {mutationOptions, queryOptions} from "@tanstack/react-query";
import * as adminApi from "./api.ts";

export const adminKeys = {
    all: ["admin-settings"] as const,
    auth: () => [...adminKeys.all, "auth"] as const,
    codeGroups: (search?: string) => [...adminKeys.all, "code-groups", search ?? ""] as const,
    codeDetails: (groupCode: string) => [...adminKeys.all, "code-details", groupCode] as const,
    users: (search?: string) => [...adminKeys.all, "users", search ?? ""] as const,
    orgs: () => [...adminKeys.all, "orgs"] as const,
};

export const adminQueries = {
    auth: () =>
        queryOptions({
            queryKey: adminKeys.auth(),
            queryFn: () => adminApi.resolveAuthSession(),
            staleTime: 30_000,
        }),
    codeGroups: (search?: string) =>
        queryOptions({
            queryKey: adminKeys.codeGroups(search),
            queryFn: () => adminApi.listCodeGroups(search),
        }),
    codeDetails: (groupCode: string) =>
        queryOptions({
            queryKey: adminKeys.codeDetails(groupCode),
            queryFn: () => adminApi.listCodeDetails(groupCode),
            enabled: Boolean(groupCode),
        }),
    users: (search?: string) =>
        queryOptions({
            queryKey: adminKeys.users(search),
            queryFn: () => adminApi.listAdminUsers(search),
        }),
    orgs: () =>
        queryOptions({
            queryKey: adminKeys.orgs(),
            queryFn: () => adminApi.listApiOrganizations(),
        }),
};

export const adminMutations = {
    login: () =>
        mutationOptions({
            mutationFn: ({loginId, password}: {loginId: string; password: string}) =>
                adminApi.adminLogin(loginId, password),
        }),
    logout: () =>
        mutationOptions({
            mutationFn: () => adminApi.adminLogout(),
        }),
    changePassword: () =>
        mutationOptions({
            mutationFn: ({currentPassword, newPassword}: {currentPassword: string; newPassword: string}) =>
                adminApi.adminChangePassword(currentPassword, newPassword),
        }),
    registerCodeGroup: () =>
        mutationOptions({
            mutationFn: adminApi.registerCodeGroup,
        }),
    updateCodeGroup: () =>
        mutationOptions({
            mutationFn: adminApi.updateCodeGroup,
        }),
    deleteCodeGroup: () =>
        mutationOptions({
            mutationFn: adminApi.deleteCodeGroup,
        }),
    registerCodeDetail: () =>
        mutationOptions({
            mutationFn: adminApi.registerCodeDetail,
        }),
    updateCodeDetail: () =>
        mutationOptions({
            mutationFn: adminApi.updateCodeDetail,
        }),
    deleteCodeDetail: () =>
        mutationOptions({
            mutationFn: ({groupCode, code}: {groupCode: string; code: string}) =>
                adminApi.deleteCodeDetail(groupCode, code),
        }),
    registerUser: () =>
        mutationOptions({
            mutationFn: adminApi.registerAdminUser,
        }),
    updateUser: () =>
        mutationOptions({
            mutationFn: adminApi.updateAdminUser,
        }),
    deleteUser: () =>
        mutationOptions({
            mutationFn: adminApi.deleteAdminUser,
        }),
    registerOrg: () =>
        mutationOptions({
            mutationFn: adminApi.registerApiOrganization,
        }),
    updateOrg: () =>
        mutationOptions({
            mutationFn: adminApi.updateApiOrganization,
        }),
    deleteOrg: () =>
        mutationOptions({
            mutationFn: adminApi.deleteApiOrganization,
        }),
};
