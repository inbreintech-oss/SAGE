export interface IUserInfo {
    id: string;
    companyId: number;
    email?: string;
    firstName?: string;
    lastName?: string;
    settings?: Record<string, unknown>;
    disabled: boolean;
    mfaEnabled: boolean;
    languageCode: string;
    createdBy: string;
    createdAt: Date;
    updatedBy: string;
    updatedAt: Date;
}