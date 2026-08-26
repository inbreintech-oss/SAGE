import BaseColumn, {type BaseColumnProps} from "./BaseColumn";
import {format as dateFormat} from "date-fns";

export type DateColumnProps<TData> = {
    record: TData;
    accessor: keyof TData | string;
    format?: string;
} & BaseColumnProps;

export default function DateColumn<TData>({
    record,
    accessor,
    textAlign = "center",
    format = "yyyy-MM-dd"
}: DateColumnProps<TData>) {
    const dateString = String(record[accessor as keyof TData]);
    const text = !isNaN(Date.parse(dateString)) ?
        dateFormat(dateString, format) :
        "";

    return (
        <BaseColumn textAlign={textAlign}>
            {text}
        </BaseColumn>
    )
}
