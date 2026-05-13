import type { PageMapItem } from "nextra";
import { getPageMap } from "nextra/page-map";
import { Layout } from "nextra-theme-docs";

import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { getLocaleByLang } from "@/core/i18n/locale";
import "nextra-theme-docs/style.css";

// Empty array hides the Nextra LocaleSwitch entirely (it short-circuits to
// null when length === 0). The product is English-only — no useless 1-item
// dropdown. See docs/plans/2026-05-14-libra-english-only-design.md §3.2.
const i18n: { locale: string; name: string }[] = [];

function formatPageRoute(base: string, items: PageMapItem[]): PageMapItem[] {
  return items.map((item) => {
    if ("route" in item && !item.route.startsWith(base)) {
      item.route = `${base}${item.route}`;
    }
    if ("children" in item && item.children) {
      item.children = formatPageRoute(base, item.children);
    }
    return item;
  });
}

export default async function DocLayout({ children, params }) {
  const { lang } = await params;
  const locale = getLocaleByLang(lang);
  const pages = await getPageMap(`/${lang}`);
  const pageMap = formatPageRoute(`/${lang}/docs`, pages);

  return (
    <Layout
      navbar={
        <Header
          className="sticky max-w-full px-10"
          homeURL="/"
          locale={locale}
        />
      }
      pageMap={pageMap}
      docsRepositoryBase="https://github.com/wisdom222/scideer/tree/scideer-main/frontend/src/content"
      footer={<Footer className="mt-0" />}
      i18n={i18n}
      // ... Your additional layout options
    >
      {children}
    </Layout>
  );
}
