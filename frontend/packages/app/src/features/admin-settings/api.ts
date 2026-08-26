import {FetchAPI, FetchAPIError} from "@/features/Utils.ts";
import type {
    AdminUser,
    ApiOrganization,
    AuthSession,
    CodeDetail,
    CodeGroup,
    SageApiResponse,
} from "./types.ts";

async function adminFetch<T>(path: string, method: string, body?: unknown): Promise<T> {
    try {
        const response = await FetchAPI<SageApiResponse<T>>(path, method, {
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
        if (!response.success) {
            throw new FetchAPIError({status: "error", message: response.error ?? "요청 실패"});
        }
        return response.result;
    } catch (error) {
        if (error instanceof FetchAPIError) {
            const message =
                (error.data as {message?: string} | undefined)?.message ??
                (error.data as {error?: string} | undefined)?.error ??
                "요청 실패";
            throw new FetchAPIError({status: "error", message});
        }
        if (error instanceof TypeError && /fetch/i.test(error.message)) {
            throw new FetchAPIError({
                status: "error",
                message:
                    "SAGE.py API 서버(8090)에 연결할 수 없습니다. 백엔드 기동 및 시드 실행을 확인하세요.",
            });
        }
        throw error;
    }
}

export async function adminLogin(loginId: string, password: string): Promise<AdminUser> {
    return adminFetch<AdminUser>("/admin/auth/login", "POST", {login_id: loginId, password});
}

export async function adminLogout(): Promise<void> {
    await adminFetch<{message: string}>("/admin/auth/logout", "POST", {});
}

export async function adminMe(): Promise<AdminUser> {
    return adminFetch<AdminUser>("/admin/auth/me", "POST", {});
}

export async function adminChangePassword(currentPassword: string, newPassword: string): Promise<AdminUser> {
    return adminFetch<AdminUser>("/admin/auth/password", "POST", {
        current_password: currentPassword,
        new_password: newPassword,
    });
}

export async function listCodeGroups(search?: string): Promise<CodeGroup[]> {
    return adminFetch<CodeGroup[]>("/admin/code/group/list", "POST", {search: search ?? null});
}

export async function registerCodeGroup(payload: {
    group_code: string;
    group_name: string;
    description?: string;
}): Promise<CodeGroup> {
    return adminFetch<CodeGroup>("/admin/code/group/register", "POST", payload);
}

export async function updateCodeGroup(payload: {
    group_code: string;
    group_name: string;
    description?: string;
    use_yn?: boolean;
}): Promise<CodeGroup> {
    return adminFetch<CodeGroup>("/admin/code/group/update", "PUT", payload);
}

export async function deleteCodeGroup(groupCode: string): Promise<void> {
    await adminFetch<{group_code: string}>("/admin/code/group/delete", "DELETE", {group_code: groupCode});
}

export async function listCodeDetails(groupCode: string): Promise<CodeDetail[]> {
    return adminFetch<CodeDetail[]>("/admin/code/detail/list", "POST", {group_code: groupCode});
}

export async function registerCodeDetail(payload: {
    group_code: string;
    code: string;
    name: string;
    sort_order: number;
}): Promise<CodeDetail> {
    return adminFetch<CodeDetail>("/admin/code/detail/register", "POST", payload);
}

export async function updateCodeDetail(payload: {
    group_code: string;
    code: string;
    name: string;
    sort_order: number;
    use_yn?: boolean;
}): Promise<CodeDetail> {
    return adminFetch<CodeDetail>("/admin/code/detail/update", "PUT", payload);
}

export async function deleteCodeDetail(groupCode: string, code: string): Promise<void> {
    await adminFetch<{group_code: string; code: string}>(
        "/admin/code/detail/delete",
        "DELETE",
        {group_code: groupCode, code},
    );
}

export async function listAdminUsers(search?: string): Promise<AdminUser[]> {
    return adminFetch<AdminUser[]>("/admin/user/list", "POST", {search: search ?? null});
}

export async function registerAdminUser(payload: {
    login_id: string;
    name: string;
    email?: string;
    password: string;
    role: AdminUser["role"];
}): Promise<AdminUser> {
    return adminFetch<AdminUser>("/admin/user/register", "POST", payload);
}

export async function updateAdminUser(payload: {
    user_id: string;
    name: string;
    email?: string;
    password?: string | null;
    role: AdminUser["role"];
    disabled?: boolean;
}): Promise<AdminUser> {
    return adminFetch<AdminUser>("/admin/user/update", "PUT", payload);
}

export async function deleteAdminUser(userId: string): Promise<void> {
    await adminFetch<{user_id: string}>("/admin/user/delete", "DELETE", {user_id: userId});
}

export async function checkLoginIdAvailable(loginId: string): Promise<boolean> {
    const result = await adminFetch<{available: boolean}>("/admin/user/check-id", "POST", {login_id: loginId});
    return result.available;
}

export async function checkEmailAvailable(email: string, excludeUserId?: string | null): Promise<boolean> {
    const result = await adminFetch<{available: boolean}>("/admin/user/check-email", "POST", {
        email,
        exclude_user_id: excludeUserId ?? null,
    });
    return result.available;
}

export async function listApiOrganizations(): Promise<ApiOrganization[]> {
    return adminFetch<ApiOrganization[]>("/admin/org/list", "POST", {});
}

export async function registerApiOrganization(payload: {
    name: string;
    code: string;
    base_url?: string;
    description?: string;
    keys: Array<{key_name: string; key_value: string}>;
}): Promise<ApiOrganization> {
    return adminFetch<ApiOrganization>("/admin/org/register", "POST", payload);
}

export async function updateApiOrganization(payload: {
    org_id: string;
    name: string;
    code: string;
    base_url?: string;
    description?: string;
    keys: Array<{key_name: string; key_value: string}>;
}): Promise<ApiOrganization> {
    return adminFetch<ApiOrganization>("/admin/org/update", "PUT", payload);
}

export async function deleteApiOrganization(orgId: string): Promise<void> {
    await adminFetch<{org_id: string}>("/admin/org/delete", "DELETE", {org_id: orgId});
}

export async function resolveAuthSession(): Promise<AuthSession> {
    try {
        const user = await adminMe();
        return {loggedIn: true, user};
    } catch {
        return {loggedIn: false, user: null};
    }
}
