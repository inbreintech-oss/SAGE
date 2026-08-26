import type {Preview} from "@storybook/react-vite";
import {MantineProvider, createTheme} from "@mantine/core";
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';

const preview: Preview = {
    parameters: {
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/i,
            },
        },

        a11y: {
            // 'todo' - show a11y violations in the test UI only
            // 'error' - fail CI on a11y violations
            // 'off' - skip a11y checks entirely
            test: "todo"
        }
    },
    decorators: [
        (Story, context) => {
            const theme = createTheme({});

            return (
                <MantineProvider theme={theme}>
                    <Story {...context} />
                </MantineProvider>
            )
        }
    ]
};

export default preview;
