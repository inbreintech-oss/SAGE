import {create} from "zustand";
import {devtools} from "zustand/middleware";
import type {Menu} from "@/libs/types";

interface IMenuState {
    currentMenu: Menu | null;
    setCurrentMenu: (menu: Menu | null) => void;
}

const useMenuStore = create<IMenuState>()(
    devtools(
        (set) => ({
            currentMenu: null,
            setCurrentMenu: (menu: Menu | null) => set(() => ({currentMenu: menu})),
        }),
        {
            name: "menu-store"
        }
    )
)

export default useMenuStore;
