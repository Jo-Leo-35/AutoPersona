import { SHOPEE_URLS } from "./selectors.js";

/**
 * @param {import("playwright").Page} page
 */
export async function openSellerCenter(page) {
  await page.goto(SHOPEE_URLS.newProduct, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
}
