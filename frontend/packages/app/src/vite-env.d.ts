/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_SAGE_API_KEY?: string;
    readonly VITE_SAGE_THEME?: string;
    /** dev: React Query Devtools — "true" 일 때만 우측 하단 표시 (기본 숨김) */
    readonly VITE_ENABLE_RQ_DEVTOOLS?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

declare namespace NodeJs {
    interface ProcessEnv {
        BREWSYNC_CLIENT_PORT: string;
        BREWSYNC_API_URL: string;
        BREWSYNC_API_ENDPOINT: string;       
    }
}

declare module "*.txt?raw" {
    const content: string;
    export default content;
  }
  