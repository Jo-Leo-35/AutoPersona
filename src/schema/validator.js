import fs from "node:fs";
import path from "node:path";
import { AUTOMATION_MODES, PRODUCT_CONDITIONS } from "./listing.schema.js";

/**
 * @typedef {import("./listing.schema.js").ListingSchema} ListingSchema
 * @typedef {{ path: string, message: string }} ValidationIssue
 * @typedef {{ errors: ValidationIssue[], warnings: ValidationIssue[] }} ValidationResult
 */

const hasText = (value) => typeof value === "string" && value.trim().length > 0;
const isPositiveNumber = (value) => typeof value === "number" && Number.isFinite(value) && value > 0;
const isNonNegativeNumber = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;

/**
 * @param {ListingSchema} listing
 * @param {{ baseDir?: string }=} options
 * @returns {ValidationResult}
 */
export function validateListing(listing, options = {}) {
  const errors = [];
  const warnings = [];
  const baseDir = options.baseDir ?? process.cwd();

  const error = (pathName, message) => errors.push({ path: pathName, message });
  const warn = (pathName, message) => warnings.push({ path: pathName, message });

  if (!listing || typeof listing !== "object") {
    return {
      errors: [{ path: "$", message: "Listing must be a JSON object." }],
      warnings
    };
  }

  if (!hasText(listing.product?.title)) {
    error("product.title", "Product title is required.");
  }

  if (!Array.isArray(listing.product?.categoryPath) || listing.product.categoryPath.length === 0) {
    error("product.categoryPath", "At least one category path item is required.");
  }

  if (!PRODUCT_CONDITIONS.includes(listing.product?.condition)) {
    error("product.condition", "Condition must be either 'new' or 'used'.");
  }

  if (!isPositiveNumber(listing.sales?.price)) {
    error("sales.price", "Price must be greater than 0.");
  }

  if (!isNonNegativeNumber(listing.sales?.stock)) {
    error("sales.stock", "Stock must be 0 or greater.");
  }

  if (!isPositiveNumber(listing.shipping?.weightKg)) {
    error("shipping.weightKg", "Weight in kilograms is required and must be greater than 0.");
  }

  for (const key of ["width", "length", "height"]) {
    if (!isPositiveNumber(listing.shipping?.packageSizeCm?.[key])) {
      error(`shipping.packageSizeCm.${key}`, `${key} must be greater than 0.`);
    }
  }

  if (typeof listing.shipping?.dangerousGoods !== "boolean") {
    error("shipping.dangerousGoods", "Dangerous goods must be explicitly true or false.");
  }

  if (!Array.isArray(listing.media?.imagePaths) || listing.media.imagePaths.length === 0) {
    error("media.imagePaths", "At least one product image path is required.");
  } else {
    listing.media.imagePaths.forEach((imagePath, index) => {
      if (!hasText(imagePath)) {
        error(`media.imagePaths.${index}`, "Image path cannot be empty.");
        return;
      }

      const resolved = path.isAbsolute(imagePath) ? imagePath : path.resolve(baseDir, imagePath);
      if (!fs.existsSync(resolved)) {
        warn(`media.imagePaths.${index}`, `Image path does not exist yet: ${imagePath}`);
      }
    });
  }

  if (!AUTOMATION_MODES.includes(listing.automation?.mode)) {
    error("automation.mode", `Mode must be one of: ${AUTOMATION_MODES.join(", ")}.`);
  }

  if (listing.automation?.allowPublish !== false) {
    error("automation.allowPublish", "allowPublish must be explicitly false.");
  }

  if (listing.compliance?.hasBSMI === true && !hasText(listing.compliance.bsmiNumber)) {
    error("compliance.bsmiNumber", "BSMI number is required when hasBSMI is true.");
  }

  if (listing.compliance?.hasNCC === true && !hasText(listing.compliance.nccNumber)) {
    error("compliance.nccNumber", "NCC number is required when hasNCC is true.");
  }

  if (listing.product?.noValidGtin !== true && !hasText(listing.product?.gtin)) {
    warn("product.gtin", "GTIN is missing. Set noValidGtin to true only when confirmed.");
  }

  if (!hasText(listing.product?.model)) {
    warn("product.model", "Model is missing or incomplete. Do not infer it from images.");
  }

  if (!hasText(listing.compliance?.warrantyPeriod) && !hasText(listing.compliance?.warrantyType)) {
    warn("compliance.warranty", "Warranty information is missing.");
  }

  if (!hasText(listing.compliance?.packageContents)) {
    warn("compliance.packageContents", "Package contents are missing.");
  }

  return { errors, warnings };
}

/**
 * @param {ValidationResult} result
 * @returns {boolean}
 */
export function hasBlockingErrors(result) {
  return result.errors.length > 0;
}
