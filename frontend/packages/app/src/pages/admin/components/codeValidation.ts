/** 그룹코드명: 한글·영문·숫자·괄호 ()[]{} — 완성형 음절 기준 */
const GROUP_NAME_FULL = /^[\uAC00-\uD7A3a-zA-Z0-9()[\]{}]+$/;
/** 그룹코드·상세코드: 영문·숫자 */
const CODE_ALLOWED = /[^a-zA-Z0-9]/g;
const CODE_FULL = /^[a-zA-Z0-9]+$/;

export function sanitizeCode(value: string): string {
    return value.replace(CODE_ALLOWED, "");
}
export function validateGroupName(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return "그룹코드명을 입력해 주세요.";
    if (!GROUP_NAME_FULL.test(trimmed)) {
        return "그룹코드명은 한글, 영문, 숫자, 괄호 ()[]{} 만 입력 가능합니다.";
    }
    return null;
}

export function validateGroupCode(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return "그룹코드를 입력해 주세요.";
    if (!CODE_FULL.test(trimmed)) {
        return "그룹코드는 영문, 숫자만 입력 가능합니다.";
    }
    return null;
}

export function validateDetailCode(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return "코드를 입력해 주세요.";
    if (!CODE_FULL.test(trimmed)) {
        return "코드는 영문, 숫자만 입력 가능합니다.";
    }
    return null;
}

export function validateDetailName(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return "명칭을 입력해 주세요.";
    if (!GROUP_NAME_FULL.test(trimmed)) {
        return "명칭은 한글, 영문, 숫자, 괄호 ()[]{} 만 입력 가능합니다.";
    }
    return null;
}
