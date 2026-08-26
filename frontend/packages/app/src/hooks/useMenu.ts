import {useMenuStore} from "@/libs/stores";
import {useEffect} from "react";
import {useLocation} from "react-router-dom";
import {useMenuList} from "@/features/menu";

/**
 * 메뉴 관련 상태와 쿼리를 관리하는 커스텀 훅
 */
export function useMenu() {
    const {currentMenu, setCurrentMenu} = useMenuStore();
    const {data, isLoading} = useMenuList();
    const location = useLocation();

    useEffect(() => {
        const menus = data?.items ?? [];
        const next = menus.find(m => m.url === location.pathname) || null;
        // 동일 참조/동일 id면 스킵 — 불필요 리렌더로 ScrollArea·flex 재측정 유발 방지
        if ((currentMenu?.id ?? null) === (next?.id ?? null)) return;
        setCurrentMenu(next);
    }, [data, location.pathname, setCurrentMenu, currentMenu?.id]);

    return {
        menus: data?.items ?? [],
        isMenuLoading: isLoading,
        currentMenu,
        setCurrentMenu,
    }
}
