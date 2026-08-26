import {
    Box, Flex, Text, Tree as MantineTree, type TreeProps as MantineTreeProps
} from "@mantine/core";
import TreeNode from "./TreeNode";

export type TreeMode = "check" | "select";

export type TreeProps = {
    title?: string;
    selectOne?: boolean;
    mode?: TreeMode;
} & MantineTreeProps;

export default function Tree({
    title,
    data,
    w,
    h,
    tree,
    selectOne = false,
    mode = "check",
    ...rest
}: TreeProps) {
    return (
        <Flex direction="column" bd="1px solid gray.3"
              style={{overflow: "hidden"}}
              w={w}
              h={h}
        >
            {title && (
                <Box bg="white"
                     style={{
                         borderBottom: "1px solid var(--mantine-color-gray-3)"
                     }}
                     px="xs"
                     py={4}
                >
                    <Text size="sm" fw="bold">
                        {title}
                    </Text>
                </Box>
            )}
            <Box flex={1}
                 style={{
                     overflow: "auto",
                 }}
            >
                <MantineTree {...rest}
                             tree={tree}
                             flex={1}
                             p="xs"
                             data={data}
                             renderNode={(payload) => (
                                 <TreeNode {...payload} selectOne={selectOne} mode={mode} />
                             )}
                />
            </Box>
        </Flex>
    )
}
