import type { DbForm } from "./types";

const IP_REGEX = /^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$/;
const PORT_REGEX = /^\d{4}$/;
const DB_IDENTIFIER_REGEX = /^[a-zA-Z_][a-zA-Z0-9_]{0,62}$/;
const SQL_KEYWORD_REGEX = /^\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b/i;
const USERNAME_REGEX = /^[a-zA-Z_][a-zA-Z0-9_]{0,62}$/;

export function sanitizeHost(value: string): string {
    return value.replace(/[^0-9.]/g, "").slice(0, 15);
}

export function sanitizePort(value: string): string {
    return value.replace(/\D/g, "").slice(0, 4);
}

export function sanitizeDbIdentifier(value: string): string {
    return value.replace(/[^a-zA-Z0-9_]/g, "").slice(0, 63);
}

export function sanitizeDbUsername(value: string): string {
    return value.replace(/[^a-zA-Z0-9_]/g, "").slice(0, 63);
}

export function sanitizeDbPassword(value: string): string {
    return value.slice(0, 128);
}

export function sanitizeSqlQuery(value: string): string {
    return value.slice(0, 4096);
}

export function isValidHost(host: string): boolean {
    return IP_REGEX.test(host);
}

export function isValidPort(port: string): boolean {
    return PORT_REGEX.test(port);
}

export function isValidDbIdentifier(name: string): boolean {
    return DB_IDENTIFIER_REGEX.test(name);
}

export function isValidUsername(name: string): boolean {
    return USERNAME_REGEX.test(name);
}

export function isValidSqlQuery(query: string): boolean {
    if (!query.trim()) return true;
    return SQL_KEYWORD_REGEX.test(query);
}

export function validateDbForm(form: DbForm): string | null {
    if (!isValidHost(form.host)) return "HOST는 유효한 IP Address 형식이어야 합니다.";
    if (!isValidPort(form.port)) return "PORT는 정확히 4자리 숫자여야 합니다.";
    if (!isValidDbIdentifier(form.dbName)) return "DB NAME은 영문/숫자/언더스코어 명명 규칙을 따라야 합니다.";
    if (!isValidDbIdentifier(form.tableName)) return "TABLE NAME은 영문/숫자/언더스코어 명명 규칙을 따라야 합니다.";
    if (!isValidUsername(form.username)) return "USER는 영문/숫자/언더스코어 명명 규칙을 따라야 합니다.";
    if (!form.password.trim()) return "PASSWORD를 입력해주세요.";
    if (!isValidSqlQuery(form.query)) return "SCHEMA FETCH QUERY는 ANSI SQL 구문 형식이어야 합니다.";
    return null;
}
