import { resolveProviderCode, type ProviderCode } from "@/libs/stores/toolManagement/commonCodes";

export function mapApiProviderToUi(
    provider: string | null | undefined,
    fallback: ProviderCode = "PROV_KIS",
): ProviderCode {
    return resolveProviderCode(provider, fallback);
}
