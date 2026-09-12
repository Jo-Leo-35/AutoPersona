/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 * @typedef {import("../schema/validator.js").ValidationResult} ValidationResult
 */

/**
 * @param {ListingSchema} listing
 * @param {ValidationResult} validation
 * @returns {string}
 */
export function buildReviewSummary(listing, validation) {
  const size = listing.shipping.packageSizeCm;
  const imageCount = listing.media.imagePaths.length;

  const lines = [
    "AutoPersona Review Summary",
    "",
    `商品名稱: ${listing.product.title}`,
    `分類: ${listing.product.categoryPath.join(" > ")}`,
    `品牌: ${listing.product.brand ?? "未提供"}`,
    `型號: ${listing.product.model ?? "未提供"}`,
    `商品狀況: ${listing.product.condition}`,
    `售價: ${listing.sales.price}`,
    `庫存: ${listing.sales.stock}`,
    `重量: ${listing.shipping.weightKg} kg`,
    `包裹尺寸: ${size.width} x ${size.length} x ${size.height} cm`,
    `BSMI: ${listing.compliance.hasBSMI ? listing.compliance.bsmiNumber ?? "缺字號" : "否"}`,
    `NCC: ${listing.compliance.hasNCC ? listing.compliance.nccNumber ?? "缺字號" : "否"}`,
    `GTIN: ${listing.product.gtin ?? (listing.product.noValidGtin ? "確認無有效 GTIN" : "未提供")}`,
    `圖片數量: ${imageCount}`,
    "",
    `Blocking errors: ${validation.errors.length}`,
    `Warnings: ${validation.warnings.length}`
  ];

  if (validation.errors.length > 0) {
    lines.push("", "Errors:");
    validation.errors.forEach((issue) => lines.push(`- ${issue.path}: ${issue.message}`));
  }

  if (validation.warnings.length > 0) {
    lines.push("", "Warnings:");
    validation.warnings.forEach((issue) => lines.push(`- ${issue.path}: ${issue.message}`));
  }

  lines.push("", "Publish action: disabled. Human review required.");
  return lines.join("\n");
}
