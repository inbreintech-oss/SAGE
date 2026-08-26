import type { JSX } from "react";
import type { ExtraProps } from "react-markdown";

export type MdProps<K extends keyof JSX.IntrinsicElements> = JSX.IntrinsicElements[K] & ExtraProps;
