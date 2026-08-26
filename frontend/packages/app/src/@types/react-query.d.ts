import "@tanstack/react-query";
import {FetchAPIError} from "@/libs/apis/Utils.ts";

// React Query 전역 에러 타입 변경
declare module "@tanstack/react-query" {
    interface Register {
        defaultError: FetchAPIError
    }
}