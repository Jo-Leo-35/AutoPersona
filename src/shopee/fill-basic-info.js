import { selectors } from "./selectors.js";

/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {ListingSchema} listing
 */
export async function fillBasicInfo(page, listing) {
  await page.locator(selectors.titleInput).fill(listing.product.title);

  if (listing.product.noValidGtin === true) {
    await page.getByText("商品無有效的國際條碼", { exact: false }).click();
  } else if (listing.product.gtin) {
    await page.locator(selectors.gtinInput).first().fill(listing.product.gtin);
  }

  // Category selection is intentionally left as a review point because Shopee's
  // category picker changes often and should be mapped per store/category.
}
