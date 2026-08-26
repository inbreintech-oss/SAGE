import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {adminMutations, adminQueries, adminKeys} from "./queries.ts";
import type {AdminUser} from "./types.ts";

export function useAdminAuth() {
    return useQuery(adminQueries.auth());
}

export function useAdminLogin() {
    const qc = useQueryClient();
    return useMutation({
        ...adminMutations.login(),
        onSuccess: (user: AdminUser) => {
            qc.setQueryData(adminKeys.auth(), {loggedIn: true, user});
        },
    });
}

export function useAdminLogout() {
    const qc = useQueryClient();
    return useMutation({
        ...adminMutations.logout(),
        onSuccess: () => {
            qc.setQueryData(adminKeys.auth(), {loggedIn: false, user: null});
        },
    });
}

export function useAdminChangePassword() {
    const qc = useQueryClient();
    return useMutation({
        ...adminMutations.changePassword(),
        onSuccess: (user: AdminUser) => {
            qc.setQueryData(adminKeys.auth(), {loggedIn: true, user});
        },
    });
}

export function useCodeGroups(search?: string) {
    return useQuery(adminQueries.codeGroups(search));
}

export function useCodeDetails(groupCode: string) {
    return useQuery(adminQueries.codeDetails(groupCode));
}

export function useAdminUsers(search?: string) {
    return useQuery(adminQueries.users(search));
}

export function useApiOrganizations() {
    return useQuery(adminQueries.orgs());
}

export {
    adminMutations,
    adminQueries,
    adminKeys,
} from "./queries.ts";
