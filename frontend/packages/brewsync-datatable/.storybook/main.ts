import type {StorybookConfig} from "@storybook/react-vite";
import viteTsConfig from "vite-tsconfig-paths";
import viteTsConfigPaths from "vite-tsconfig-paths";
import {mergeConfig} from "vite";

const config: StorybookConfig = {
    stories: [
        "../stories/*.mdx",
        "../stories/*.stories.@(js|jsx|mjs|ts|tsx)"
    ],
    addons: [
        "@chromatic-com/storybook",
        "@storybook/addon-docs",
        "@storybook/addon-onboarding",
        "@storybook/addon-a11y",
        "@storybook/addon-vitest"
    ],
    framework: {
        name: "@storybook/react-vite",
        options: {}
    },
    async viteFinal(config) {
        return mergeConfig(config, {
            plugins: [viteTsConfig(), viteTsConfigPaths()],
            css: {
                modules: {
                    localsConvention: "camelCaseOnly"
                }
            }
        })
    }
}

export default config;
