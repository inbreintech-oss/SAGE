import {type DataTableColumn} from "mantine-datatable";
import {TextColumn, DateColumn, BooleanColumn} from "./columns";

export type DateColumnOptions<TData> = {
    formatString?: string,
} & DataTableColumn<TData>

export const ColumnHelper = {
    hiddenColumn: <TData, >({
        accessor,
    }: Pick<DataTableColumn<TData>, "accessor">): DataTableColumn<TData> => ({
        accessor: accessor,
        hidden: true,
    }),
    textColumn: <TData, >({
        accessor,
        title,
        textAlign,
        ...rest
    }: DataTableColumn<TData>): DataTableColumn<TData> => ({
        accessor: accessor,
        title: title,
        textAlign: "center",
        render: (record, index) => (
            <TextColumn key={index} record={record} accessor={accessor} textAlign={textAlign} />
        ),
        ...rest,
    }),
    dateColumn: <TData, >({
        accessor,
        title,
        textAlign,
        formatString,
        ...rest
    }: DateColumnOptions<TData>): DataTableColumn<TData> => ({
        accessor: accessor,
        title: title,
        textAlign: "center",
        render: (record, index) => (
            <DateColumn key={index} record={record} accessor={accessor} textAlign={textAlign || "center"}
                        format={formatString}
            />
        ),
        ...rest
    }),
    booleanColumn: <TData, >({
        accessor,
        title,
        ...rest
    }: DataTableColumn<TData>): DataTableColumn<TData> => ({
        accessor: accessor,
        title: title,
        render: (record, index) => (
            <BooleanColumn key={index} record={record} accessor={accessor} />
        ),
        ...rest
    })
};
