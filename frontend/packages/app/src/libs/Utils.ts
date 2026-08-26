import type {Menu} from "@/libs/types";
import * as XLSX from "xlsx";

/**
 * 텍스트를 SHA-256 해시로 변환합니다.
 * @param {string} plainText
 * @returns {Promise<string>}
 * @constructor
 */
export async function createHash(plainText: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(plainText); // Encode the string to a Uint8Array

    const hashBuffer = await crypto.subtle.digest('SHA-256', data); // Calculate the hash
    const hashArray = Array.from(new Uint8Array(hashBuffer)); // Convert buffer to array of bytes

    return hashArray.map(b => b.toString(16).padStart(2, '0')).join(''); // Convert bytes to hex string
}

/**
 * 대상 메뉴를 기준으로 부모 메뉴를 재귀적으로 찾아서 경로에 해당하는 메뉴 리스트를 반환합니다.
 * @param {Menu[]} menus
 * @param {number} menuId
 * @returns {Menu[]}
 */
export function getMenuPath(menus: Menu[], menuId: number): Menu[] {
    const path: Menu[] = [];
    const menuMap = new Map<number, Menu>();

    // 메뉴 ID를 키로, 메뉴 객체를 값으로 하는 맵 생성
    menus.forEach(menu => {
        if (menu.id) {
            menuMap.set(menu.id, menu);
        }
    });

    let currentMenu = menuMap.get(menuId);

    // 현재 메뉴가 존재하는 동안 반복
    while (currentMenu) {
        path.unshift(currentMenu); // 현재 메뉴를 경로의 시작 부분에 추가
        if (currentMenu.parentId) {
            currentMenu = menuMap.get(currentMenu.parentId); // 부모 메뉴로 이동
        } else {
            break; // 부모 메뉴가 없으면 종료
        }
    }

    return path;
}

export type ExcelRow = Record<string, unknown>;

/**
 * File -> ArrayBuffer -> Workbook -> JSON rows
 * @param file 사용자가 업로드한 엑셀 파일
 * @param sheetName 특정 시트명(없으면 첫 시트)
 */
export async function readExcelFromFile(file: File, sheetName?: string) {
    const buf = await file.arrayBuffer();

    // type: "array" 를 쓰면 ArrayBuffer 기반으로 읽음
    const wb = XLSX.read(buf, { type: "array" });

    const targetSheetName = sheetName ?? wb.SheetNames[0];
    const ws = wb.Sheets[targetSheetName];
    if (!ws) throw new Error(`Sheet not found: ${targetSheetName}`);

    // header: 1 -> 2D array로 받기 (원하면)
    // const rows2d = XLSX.utils.sheet_to_json(ws, { header: 1 });

    // 기본: 첫 행을 header로 잡아 객체 배열로 변환
    const rows = XLSX.utils.sheet_to_json<ExcelRow>(ws, {
        defval: "",       // 빈 셀 기본값
        raw: true,        // 숫자/날짜 포맷을 최대한 raw로
        // dateNF: "yyyy-mm-dd", // 필요하면
    });

    return {
        sheetName: targetSheetName,
        rows,
    };
}

/**
 * bytes 크기를 사람이 읽기 쉬운 문자열로 변환합니다.
 * @param bytes 변환할 바이트 수
 * @param decimals 표시할 소수점 자리수 (기본값: 2)
 * @returns 포맷팅된 문자열 (예: '12.5 MB', '123.12 KB')
 */
export const formatBytes = (bytes: number, decimals: number = 2): string => {
    if (bytes <= 0) return '0 Bytes';

    const k = 1024; // 1000을 기준으로 하려면 이 값을 1000으로 변경
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    // 단위 배열의 인덱스 계산 (log 활용)
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    // 계산된 단위에 맞춰 값 나누기 및 소수점 고정
    const value = (bytes / Math.pow(k, i)).toFixed(decimals);

    // parseFloat를 감싸주면 '12.00 MB' 같은 경우 '12 MB'로 깔끔하게 떨어집니다.
    // 무조건 .00을 유지해야 한다면 parseFloat를 제거하세요.
    return `${parseFloat(value)} ${sizes[i]}`;
};