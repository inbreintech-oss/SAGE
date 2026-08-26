import {queryOptions} from "@tanstack/react-query";
import {    getMenuList,} from "./api";

// Query Keys
export const keys = {
    menuList: () => ["menuList"],
}

// Query Options
export const queries = {
    getMenuList: () => queryOptions({
        queryKey: keys.menuList(),
        queryFn: () => getMenuList()
    }),
}
