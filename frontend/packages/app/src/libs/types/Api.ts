export type Entity<T> = {
    [K in keyof T]: T[K];
}

export type ApiResponseBase = Entity<{
    status: "ok" | "error" | "validation" | string;
    message?: string;
}>

export type ApiItemResponse<T> = Entity<{
    item?: T;
}> & ApiResponseBase;

export type ApiListResponse<T> = Entity<{
    items?: T;
}> & ApiResponseBase;

export type ApiMutationResponse = Entity<{
    count: number;
}> & ApiResponseBase;

export type BaseEntity = {
    createdBy: string;
    createdAt: Date;
    updatedBy: string;
    updatedAt: Date;
}

export type Application = {
    id: number;
    appName: string;
    description: string;
} & BaseEntity;

export type Author = {
    id: number;
    companyAppId: number;
    authorName: string;
} & BaseEntity;

export type AuthorMenu = {
    authorId: number;
    menuId: number;
} & BaseEntity;

export type CodeDetail = {
    codeId: string;
    codeGroupId: string;
    codeName: string;
    companyAppId: number;
    korCodeName?: string;
    engCodeName?: string;
    chiCodeName?: string;
    vieCodeName?: string;
    jpnCodeName?: string;
    option1?: string;
    option2?: string;
    option3?: string;
    option4?: string;
    option5?: string;
    description?: string;
    displayOrder?: number;
    useYn?: boolean;
} & BaseEntity;

export type CodeGroup = {
    codeGroupId: string;
    companyAppId: number;
    korCodeGroupName?: string;
    engCodeGroupName?: string;
    chiCodeGroupName?: string;
    vieCodeGroupName?: string;
    jpnCodeGroupName?: string;
    description?: string;
    optionDescription1?: string;
    optionDescription2?: string;
    optionDescription3?: string;
    optionDescription4?: string;
    optionDescription5?: string;
    useYn?: boolean;
} & BaseEntity;

export type CodeHelp = {
    codeHelpId: string;
    companyAppId: number;
    commandType?: string;
    commandText?: string;
    codeColumnId?: string;
    valueColumnId?: string;
    description?: string;
    useYn?: boolean;
} & BaseEntity;

export type CompanyApplication = {
    id: number;
    appId: number;
    companyId: number;
    companyName: string;
    korAppName?: string;
    engAppName?: string;
    chiAppName?: string;
    vieAppName?: string;
    jpnAppName?: string;
} & BaseEntity;

export type Company = {
    id: number;
    korCompanyName: string;
    engCompanyName?: string;
    chiCompanyName?: string;
    vieCompanyName?: string;
    jpnCompanyName?: string;
    startDate?: Date;
    endDate?: Date;
    useYn?: boolean;
} & BaseEntity;

export type Control = {
    id: number;
    companyAppId: number;
    controlType: string;
    korControlName?: string;
    engControlName?: string;
    chiControlName?: string;
    vieControlName?: string;
    jpnControlName?: string;
    displayOrder?: number;
    useYn?: boolean;
} & BaseEntity;

export type Menu = {
    id: number;
    companyAppId: number;
    parentId?: number;
    korMenuName?: string;
    engMenuName?: string;
    chiMenuName?: string;
    vieMenuName?: string;
    jpnMenuName?: string;
    url?: string;
    level?: number;
    displayOrder?: number;
    useYn?: boolean;
} & BaseEntity;

export type User = {
    id: string;
    companyId: number;
    email?: string;
    firstName?: string;
    lastName?: string;
    password?: string;
    // TODO: 수정
    personalizationAnswers?: Record<string, string>;
    // TODO: 수정
    settings?: Record<string, unknown>;
    disabled: boolean;
    mfaEnabled: boolean;
    mfaRecoveryCodes?: string[];
    languageCode: string;
} & BaseEntity;

export type Role = {
    id: number;
    companyAppId: number;
    roleType: string;
    roleName: string;
} & BaseEntity;
