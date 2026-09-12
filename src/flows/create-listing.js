import path from "node:path";
import { generateListingContent } from "../persona/persona-engine.js";
import { validateListing, hasBlockingErrors } from "../schema/validator.js";
import { openSellerCenter } from "../shopee/open-seller-center.js";
import { fillBasicInfo } from "../shopee/fill-basic-info.js";
import { uploadImages } from "../shopee/upload-images.js";
import { fillAttributes } from "../shopee/fill-attributes.js";
import { fillDescription } from "../shopee/fill-description.js";
import { fillSales } from "../shopee/fill-sales.js";
import { fillShipping } from "../shopee/fill-shipping.js";
import { buildReviewSummary } from "../shopee/review-summary.js";

/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {ListingSchema} listing
 * @returns {ListingSchema}
 */
export function withGeneratedContent(listing) {
  const generated = generateListingContent(listing);
  return {
    ...listing,
    content: {
      ...generated,
      ...listing.content,
      description: listing.content?.description || generated.description,
      highlights: listing.content?.highlights || generated.highlights,
      keywords: listing.content?.keywords || generated.keywords
    }
  };
}

/**
 * @param {ListingSchema} listing
 * @param {{ productFilePath: string }} options
 */
export function createDraft(listing, options) {
  const baseDir = path.dirname(options.productFilePath);
  const enriched = withGeneratedContent(listing);
  const validation = validateListing(enriched, { baseDir });
  const summary = buildReviewSummary(enriched, validation);
  return { listing: enriched, validation, summary };
}

/**
 * @param {ListingSchema} listing
 * @param {{ productFilePath: string }} options
 */
export async function fillShopeeForm(listing, options) {
  const draft = createDraft(listing, options);
  if (hasBlockingErrors(draft.validation)) {
    return {
      ...draft,
      skipped: true,
      reason: "Blocking validation errors must be fixed before opening Shopee."
    };
  }

  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  const baseDir = path.dirname(options.productFilePath);

  await openSellerCenter(page);
  await uploadImages(page, draft.listing.media.imagePaths, { baseDir });
  await fillBasicInfo(page, draft.listing);
  await fillAttributes(page, draft.listing);
  await fillDescription(page, draft.listing);
  await fillSales(page, draft.listing);
  await fillShipping(page, draft.listing);

  return {
    ...draft,
    skipped: false,
    browser,
    page,
    note: "Shopee form filled. Browser intentionally left open for human review. Do not auto-publish."
  };
}
