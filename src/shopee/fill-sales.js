/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {ListingSchema} listing
 */
export async function fillSales(page, listing) {
  const inputs = page.locator('input[placeholder="Input"]');
  await inputs.nth(1).fill(String(listing.sales.price));
  await inputs.nth(2).fill(String(listing.sales.stock));

  if (listing.sales.minPurchaseQty) {
    await inputs.nth(3).fill(String(listing.sales.minPurchaseQty));
  }
}
