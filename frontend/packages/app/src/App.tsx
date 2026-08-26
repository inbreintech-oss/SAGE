import {useEffect} from "react";
import {QueryClientProvider, QueryClient} from "@tanstack/react-query";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import {MantineProvider} from "@mantine/core"
import {ModalsProvider} from "@mantine/modals";
import {Notifications} from "@mantine/notifications";
import {modals} from "@/modals";
import {CodeHighlightAdapterProvider, createShikiAdapter} from '@mantine/code-highlight';
import {getThemePreset} from "@/design-tokens/mantine";
import AppRouter from "@/libs/router/AppRouter";

const {theme, cssVariablesResolver} = getThemePreset("recommended");

import "@mantine/core/styles.layer.css"
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/code-highlight/styles.css";
import '@mantine/dropzone/styles.css';
import "brewsync-datatable/dist/styles.css";
import 'katex/dist/katex.min.css'
import "./index.css"

import "./i18n";

// eslint-disable-next-line react-refresh/only-export-components
export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
        }
    }
});

async function loadShiki() {
    const { createHighlighter } = await import("shiki");
    const shiki = await createHighlighter({
        langs: ["js", "jsx", "typescript", "tsx", "csharp", "python", "html", "json", "csv"],
        themes: []
    });

    return shiki;
}

const shikiAdapter = createShikiAdapter(loadShiki);

/** dev 전용 — .env VITE_ENABLE_RQ_DEVTOOLS=true 일 때만 우측 하단 Devtools 표시 */
const showReactQueryDevtools =
    import.meta.env.DEV && import.meta.env.VITE_ENABLE_RQ_DEVTOOLS === "true";

export default function App() {
    useEffect(() => {
        document.body.classList.toggle("hide-rq-devtools", !showReactQueryDevtools);
        return () => document.body.classList.remove("hide-rq-devtools");
    }, []);

    return (
        <QueryClientProvider client={queryClient}>
            <MantineProvider
                theme={theme}
                cssVariablesResolver={cssVariablesResolver}
                defaultColorScheme="auto"
            >
                <Notifications autoClose={2500} position="top-right"/>
                <ModalsProvider modals={modals}>
                    <CodeHighlightAdapterProvider adapter={shikiAdapter}>
                        <AppRouter/>
                    </CodeHighlightAdapterProvider>
                </ModalsProvider>
            </MantineProvider>
            {showReactQueryDevtools && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
    )
}
