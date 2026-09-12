/**
 * @typedef {"new" | "used"} ProductCondition
 * @typedef {"draft_only" | "fill_form" | "review_only" | "codex_assist"} AutomationMode
 *
 * @typedef {Object} ListingSchema
 * @property {Object} product
 * @property {string} product.title
 * @property {string[]} product.categoryPath
 * @property {string=} product.brand
 * @property {string=} product.model
 * @property {ProductCondition} product.condition
 * @property {string=} product.gtin
 * @property {boolean=} product.noValidGtin
 * @property {Object} persona
 * @property {string[]} persona.audience
 * @property {string[]} persona.useCases
 * @property {string[]} persona.painPoints
 * @property {string} persona.positioning
 * @property {string[]=} persona.competitors
 * @property {Object=} content
 * @property {string=} content.description
 * @property {string[]=} content.highlights
 * @property {string[]=} content.keywords
 * @property {Object} compliance
 * @property {boolean=} compliance.hasBSMI
 * @property {string=} compliance.bsmiNumber
 * @property {boolean=} compliance.hasNCC
 * @property {string=} compliance.nccNumber
 * @property {string=} compliance.warrantyPeriod
 * @property {string=} compliance.warrantyType
 * @property {string=} compliance.packageContents
 * @property {Object} sales
 * @property {number} sales.price
 * @property {number} sales.stock
 * @property {number=} sales.minPurchaseQty
 * @property {Object} shipping
 * @property {number} shipping.weightKg
 * @property {Object} shipping.packageSizeCm
 * @property {number} shipping.packageSizeCm.width
 * @property {number} shipping.packageSizeCm.length
 * @property {number} shipping.packageSizeCm.height
 * @property {boolean} shipping.dangerousGoods
 * @property {Object} media
 * @property {string[]} media.imagePaths
 * @property {string=} media.videoPath
 * @property {Object} automation
 * @property {AutomationMode} automation.mode
 * @property {false} automation.allowPublish
 */

export const AUTOMATION_MODES = [
  "draft_only",
  "fill_form",
  "review_only",
  "codex_assist"
];

export const PRODUCT_CONDITIONS = ["new", "used"];

export const CONDITION_LABELS = {
  new: "全新",
  used: "二手"
};
