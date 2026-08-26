import {Meta, StoryObj} from "@storybook/react-vite";
import BrewSyncDataTable from "../src/components/BrewSyncDataTable";
import {faker} from "@faker-js/faker";
import {useDataTable, useDataTableOptions, type BrewSyncColumnDef} from "../src";
import {DensityState} from "../src/features/density";
import {JsonInput, Select} from "@mantine/core";

const meta = {
    component: BrewSyncDataTable,
    title: "DataTable",
} satisfies Meta<typeof BrewSyncDataTable>

// noinspection JSUnusedLocalSymbols
type Story = StoryObj<typeof meta>;

type Person = {
    id: number;
    firstName: string;
    lastName: string;
    createdAt: Date;
}

const columns: BrewSyncColumnDef<Person>[] = [
    {accessorKey: "id", header: "ID", meta: { contentAlign: "center", headerAlign: "center" } },
    {accessorKey: "firstName", header: "First Name"},
    {accessorKey: "lastName", header: "Last Name"},
    {accessorKey: "createdAt", header: "Created At", meta: { editingType: "date" }},
]
const data: Person[] = [...Array(100)].map((_, index) => ({
    id: index,
    firstName: faker.person.firstName(),
    lastName: faker.person.lastName(),
    createdAt: faker.date.past(),
})).concat([
    {id: 999, firstName: "test", lastName: "test", createdAt: faker.date.past()},
    {id: 1000, firstName: "test2", lastName: "test2", createdAt: faker.date.past()},
    {id: 1001, firstName: "test3", lastName: "test3", createdAt: faker.date.past()},
])

export const SimplePreview = () => {
    const options = ["xs","sm","md","lg","xl"] as DensityState[];

    const table = useDataTable(useDataTableOptions({
        columns: columns,
        data: data,
        tableHeight: 500,
        debugAll: true,
        columnResizeMode: "onEnd",
        enableMultiRowSelection: true,
        initialState: {
            density: "sm"
        }
    }));

    return (
        <>
            <Select data={options}
                    value={table.getState().density}
                    onChange={(value) => table.setDensity(value as DensityState)}
            />
            <BrewSyncDataTable table={table} />
            <JsonInput autosize value={JSON.stringify(table.getState(), null, 4)} />
        </>
    )
}

export default meta;
