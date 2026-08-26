import BaseColumn, {type BaseColumnProps} from "./BaseColumn";

export type TextColumnProps<TData> = {
    record: TData;
    accessor: keyof TData | string;
} & BaseColumnProps;

export default function TextColumn<TData>({
    record,
    accessor,
    textAlign = "left"
}: TextColumnProps<TData>) {
    const text = record[accessor as keyof TData] ?
        String(record[accessor as keyof TData]) :
        "";

    return (
        <BaseColumn textAlign={textAlign}>
            {text}
        </BaseColumn>
    )
}
