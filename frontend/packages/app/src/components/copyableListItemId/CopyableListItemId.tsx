import { memo, useCallback, useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import { useNotifications } from "@/hooks";
import classes from "./copyableListItemId.module.css";

export type CopyableListItemIdProps = {
    label: string;
    value: string;
    copiedMessage: string;
    trailing?: ReactNode;
    /** 폼 라벨 행 등 — idRow 하단 여백 제거 */
    inline?: boolean;
};

export const CopyableListItemId = memo(function CopyableListItemId({
    label,
    value,
    copiedMessage,
    trailing,
    inline = false,
}: CopyableListItemIdProps) {
    const { showSuccess, showError } = useNotifications();
    const [copied, setCopied] = useState(false);
    const copiedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => () => {
        if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    }, []);

    const handleCopy = useCallback(async (e: MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        if (!value.trim()) return;

        try {
            await navigator.clipboard.writeText(value);
            showSuccess(copiedMessage);
            setCopied(true);
            if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
            copiedTimerRef.current = setTimeout(() => setCopied(false), 1500);
        } catch {
            showError("복사에 실패했습니다.");
        }
    }, [value, copiedMessage, showSuccess, showError]);

    if (!value.trim()) return null;

    return (
        <div className={`${classes.idRow} ${inline ? classes.idRowInline : ""}`.trim()}>
            <div className={classes.idMain}>
                <button
                    type="button"
                    className={classes.idTextButton}
                    title="클릭하여 복사"
                    onClick={handleCopy}
                >
                    <span className={classes.idText}>
                        {label} : {value}
                    </span>
                </button>
                <button
                    type="button"
                    className={`${classes.copyBtn} ${copied ? classes.copyBtnCopied : ""}`}
                    title="복사"
                    aria-label={`${label} 복사`}
                    onClick={handleCopy}
                >
                    {copied ? <IconCheck size={12} /> : <IconCopy size={12} />}
                </button>
            </div>
            {trailing}
        </div>
    );
});

export default CopyableListItemId;
