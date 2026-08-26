/** SAGE.py admin API 공통 응답 */

export type SageApiResponse<T> = {
    success: boolean;
    error: string | null;
    result: T;
};

export type AdminUserRole = "admin" | "member";

export type AdminUser = {
    user_id: string;
    login_id: string;
    name: string;
    email: string;
    role: AdminUserRole;
    disabled: boolean;
    created_at?: string | null;
    updated_at?: string | null;
};

export type CodeGroup = {
    group_code: string;
    group_name: string;
    description?: string;
    use_yn?: boolean;
    created_at?: string | null;
    updated_at?: string | null;
};

export type CodeDetail = {
    detail_id: string;
    group_code: string;
    code: string;
    name: string;
    sort_order: number;
    use_yn?: boolean;
    created_at?: string | null;
    updated_at?: string | null;
};

export type ApiOrgKey = {
    key_name: string;
    value_masked?: string;
};

export type ApiOrganization = {
    org_id: string;
    name: string;
    code: string;
    base_url: string;
    secret_id: string;
    description?: string;
    auth_keys: ApiOrgKey[];
    created_at?: string | null;
    updated_at?: string | null;
};

export type AuthSession = {
    loggedIn: boolean;
    user: AdminUser | null;
};
