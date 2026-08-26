import { queryOptions } from "@tanstack/react-query";
import { dataList } from "./api";

export const keys = {
    dataList: () => ["data", "list"] as const,
};

export const queries = {
    getDataList: () => queryOptions({
        queryKey: keys.dataList(),
        queryFn: () => dataList(),
        staleTime: 60_000,
    }),
};
