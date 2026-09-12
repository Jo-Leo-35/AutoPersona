/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {ListingSchema} listing
 * @returns {string}
 */
export function buildPersonaPrompt(listing) {
  return [
    "請為 Shopee 商品頁撰寫繁體中文文案。",
    "",
    `商品名稱：${listing.product.title}`,
    `品牌：${listing.product.brand ?? "未提供"}`,
    `型號：${listing.product.model ?? "未提供"}`,
    `目標客群：${listing.persona.audience.join("、")}`,
    `使用情境：${listing.persona.useCases.join("、")}`,
    `痛點：${listing.persona.painPoints.join("、")}`,
    `定位：${listing.persona.positioning}`,
    "",
    "限制：",
    "- 不要把商品定位成專業錄音室器材，除非使用者明確要求。",
    "- 不要自行捏造 BSMI、NCC、保固、包裝內容、完整 SKU。",
    "- 強調實際使用場景與購買者在意的利益。"
  ].join("\n");
}
