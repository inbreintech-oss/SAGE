import {OnChangeFn, Updater} from "@tanstack/react-table";

/**
 * Density State Type
 */
export type DensityState = "xs" | "sm" | "md" | "lg" | "xl";

/**
 * Density 옵션을 위한 Table State 입니다.
 */
export interface DensityTableState {
    density: DensityState;
}

/**
 * Density 옵션을 위한 Table Option 입니다.
 */
export interface DensityOptions {
    enableDensity?: boolean;
    onDensityChanged?: OnChangeFn<DensityState>;
}

/**
 * Density 옵션을 위한 Table API 입니다.
 */
export interface DensityInstance {
    setDensity: (updater: Updater<DensityState>) => void;
    toggleDensity: (value?: DensityState) => void;
}
