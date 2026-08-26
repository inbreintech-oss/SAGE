import {useQuery} from "@tanstack/react-query";
import {queries} from "./queries";

/**
 * Menu List 조회 Hook
 */
export function useMenuList() {
    return useQuery({
        ...queries.getMenuList(),
    });
}
