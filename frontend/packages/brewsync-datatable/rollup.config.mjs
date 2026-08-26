import packageJson from "./package.json" with {type: "json"}
import peerDepsExternal from "rollup-plugin-peer-deps-external"
import typescript from "@rollup/plugin-typescript";
import postcss from "rollup-plugin-postcss";
import dts from "rollup-plugin-dts";
import commonjs from "@rollup/plugin-commonjs";
import nodeResolve from "@rollup/plugin-node-resolve";
import autoprefixer from "autoprefixer";

export default [
    {
        input: "src/index.ts",
        output: [
            { file: packageJson.main , format: "cjs", sourcemap: true, },
            { file: packageJson.module, format: "esm", sourcemap: true, },
        ],
        plugins: [
            peerDepsExternal(),
            typescript(),
            nodeResolve(),
            commonjs(),
            postcss({
                plugins: [autoprefixer()],
                modules: {
                    localsConvention: "camelCaseOnly"
                },
                autoModules: true,
                extract: "styles.css",
            }),
        ],
        external: [
            "@mantine/core",
            "@mantine/dates",
            "@mantine/hooks",
            "@tabler/icons-react",
            "@tanstack/react-table",
            "@tanstack/react-virtual",
            "clsx",
            "dayjs",
            "lodash",
            "react",
            "react-dom",
        ],
    },
    {
        input: "src/index.ts",
        output: [
            { file: "./dist/index.d.ts", format: "es", },
        ],
        plugins: [
            dts(),
        ]
    }
]
