import {functionalUpdate, makeStateUpdater, RowData, Table, TableFeature, Updater} from "@tanstack/react-table";
import {DensityOptions, DensityState, DensityTableState} from "@/features/density/types";

export const DensityFeature: TableFeature<any> = {
    // Table의 Initial State를 설정합니다.
    getInitialState: (state): DensityTableState => {
        return {
            density: "sm",
            ...state
        }
    },

    // TableOption의 기본 값을 설정합니다.
    getDefaultOptions: <TData extends RowData>(
        table: Table<TData>
    ): DensityOptions => {
        return {
            enableDensity: true,
            onDensityChanged: makeStateUpdater("density", table),
        }
    },

    // ColumnDef의 기본 값을 설정합니다. (meta)
    //getDefaultColumnDef

    // TableInstance의 기본 Feature를 설정합니다.
    createTable: <TData extends RowData>(
        table: Table<TData>
    ): void => {
        table.setDensity = updater => {
            const safeUpdater: Updater<DensityState> = old => {
                return functionalUpdate(updater, old);
            }

            return table.options.onDensityChanged?.(safeUpdater);
        }

        table.toggleDensity = value => {
            table.setDensity(old => {
                if (value) {
                    return value;
                } else {
                    switch (old) {
                        case "xl":
                            return "lg";
                        case "lg":
                        default:
                            return "md";
                        case "md":
                            return "sm";
                        case "sm":
                            return "xs";
                        case "xs":
                            return "xl";
                    }
                }
            })
        }
    }
}
