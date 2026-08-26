export type ResponseStatus = "ok" | "error" | "validation";

export interface IResponseMaster {
    status: ResponseStatus;
    message?: string;
}