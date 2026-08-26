import path from "path";
import {defineConfig, loadEnv} from 'vite'
import react from '@vitejs/plugin-react'

/** Node(Vite) proxy — Windows에서 localhost → ::1 로 해석되어 ECONNREFUSED 나는 경우 방지 */
function resolveProxyTarget(url: string | undefined, fallback = "http://127.0.0.1:8090"): string {
    const raw = (url ?? fallback).trim().replace(/^"(.*)"$/, "$1");
    try {
        const parsed = new URL(raw);
        if (parsed.hostname === "localhost") {
            parsed.hostname = "127.0.0.1";
        }
        return parsed.toString().replace(/\/$/, "");
    } catch {
        return fallback;
    }
}

/** /toolmanagement(SPA) 와 /tool/list/query(API) 구분 — /tool/ 하위 API만 백엔드로 프록시 */
function shouldProxyToolApi(pathname: string): boolean {
    return /^\/tool\/[^/?#]+/.test(pathname);
}

/** /admin/settings(SPA) 와 /admin/auth|code|user|org/*(API) 구분 */
function shouldProxyAdminApi(pathname: string): boolean {
    return /^\/admin\/(auth|code|user|org)\//.test(pathname);
}

// https://vite.dev/config/
export default defineConfig(({mode}) => {
    // 환경 변수 로드
    const env = loadEnv(mode, process.cwd(), "");
    const {
        BREWSYNC_API_URL,
        BREWSYNC_API_ENDPOINT,        
    } = env;
    const apiProxyTarget = resolveProxyTarget(BREWSYNC_API_URL);

    return {
        plugins: [react()],
        resolve: {
            alias: {
                "@": path.resolve(__dirname, "src"),
            }
        },
        server: {
            port: Number(env.BREWSYNC_CLIENT_PORT) || 5000,
            proxy: {
                [BREWSYNC_API_ENDPOINT]: {
                    target: apiProxyTarget,
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/api/, ''),
                },
                /** Tool API — /tool/list/query 등 (/toolmanagement SPA 는 제외) */
                "/tool": {
                    target: apiProxyTarget,
                    changeOrigin: true,
                    bypass(req) {
                        const pathname = (req.url ?? "").split("?")[0];
                        if (!shouldProxyToolApi(pathname)) {
                            return "/index.html";
                        }
                    },
                },
                /** SecretKey API — /secret/list 등 */
                "/secret": {
                    target: apiProxyTarget,
                    changeOrigin: true,
                },
                /** Admin settings API — /admin/auth|code|user|org/* (SPA /admin/settings 는 제외) */
                "/admin": {
                    target: apiProxyTarget,
                    changeOrigin: true,
                    bypass(req) {
                        const pathname = (req.url ?? "").split("?")[0];
                        if (!shouldProxyAdminApi(pathname)) {
                            return "/index.html";
                        }
                    },
                },
            }
        },
        css: {
            modules: {
                localsConvention: 'camelCase'
            }
        }
    }
});

