import {Checkbox, Flex} from "@mantine/core";

type BooleanColumnProps<TData> = {
    record: TData;
    accessor: keyof TData | string;
};

export default function BooleanColumn<TData>({
    record,
    accessor
}: BooleanColumnProps<TData>) {
    const value = Boolean(record[accessor as keyof TData] || false);

    return (
        <Flex w="100%" justify="center" align="center">
            <Checkbox checked={value} readOnly/>
        </Flex>
    )
}
