/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {ListingSchema} listing
 */
export async function fillDescription(page, listing) {
  const description = listing.content?.description;
  if (!description) return;

  const editor = page.locator('[contenteditable="true"]').first();
  await editor.click();
  await editor.fill(description);
}
