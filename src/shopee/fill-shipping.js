import { chooseDropdownOption } from "./form-helpers.js";

/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {ListingSchema} listing
 */
export async function fillShipping(page, listing) {
  const inputs = page.locator('input[placeholder="Input"]');
  await inputs.nth(4).fill(String(listing.shipping.weightKg));

  await page.locator('input[placeholder="寬"]').fill(String(listing.shipping.packageSizeCm.width));
  await page.locator('input[placeholder="長"]').fill(String(listing.shipping.packageSizeCm.length));
  await page.locator('input[placeholder="高"]').fill(String(listing.shipping.packageSizeCm.height));

  await chooseDropdownOption(page, "禁運品", listing.shipping.dangerousGoods ? "是" : "否");
}
