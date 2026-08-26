import type {BrewSyncTableMeta} from "@/types";
import {createSafeContext} from "@mantine/core";

export type DataTableContextValue = {
    meta: BrewSyncTableMeta;
}

export const [DataTableContextProvider, useDataTableContext] = createSafeContext<DataTableContextValue>(
    "DataTableContextProvider is not found in component tree."
);
