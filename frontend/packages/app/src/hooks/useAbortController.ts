import {useCallback, useEffect, useRef} from "react";

/**
 * AbortController 생명주기를 관리하는 훅입니다.
 * SSE/스트리밍 mutation에서 공통으로 사용할 수 있습니다.
 *
 * - `getSignal()`: 새 AbortController를 생성하고 signal을 반환합니다. 기존 진행 중인 요청은 자동으로 abort됩니다.
 * - `abort()`: 현재 진행 중인 요청을 abort합니다.
 * - 컴포넌트 unmount 시 자동으로 abort됩니다.
 */
export function useAbortController() {
    const ref = useRef<AbortController | null>(null);

    useEffect(() => {
        return () => {
            ref.current?.abort();
        };
    }, []);

    const getSignal = useCallback((): AbortSignal => {
        ref.current?.abort();
        ref.current = new AbortController();
        return ref.current.signal;
    }, []);

    const abort = useCallback(() => {
        ref.current?.abort();
    }, []);

    return {getSignal, abort};
}
