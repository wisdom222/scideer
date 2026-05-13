import type { Locale } from "./locale";
import { enUS, type Translations } from "./locales";

// Locale is currently the single-element union `"en-US"`. zh-CN is
// retained on disk under locales/zh-CN.ts but unreferenced — see
// docs/plans/2026-05-14-libra-english-only-design.md.
export const translations: Record<Locale, Translations> = {
  "en-US": enUS,
};
