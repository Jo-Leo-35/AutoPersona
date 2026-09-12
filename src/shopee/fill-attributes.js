import { CONDITION_LABELS } from "../schema/listing.schema.js";
import { chooseDropdownOption } from "./form-helpers.js";

/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {ListingSchema} listing
 */
export async function fillAttributes(page, listing) {
  if (listing.product.brand) {
    await chooseDropdownOption(page, "品牌", listing.product.brand);
  }

  if (typeof listing.compliance.hasBSMI === "boolean") {
    await chooseDropdownOption(page, "是否有BSMI字號", listing.compliance.hasBSMI ? "是" : "否");
  }

  await chooseDropdownOption(page, "連接類型", "有線");
  await chooseDropdownOption(page, "商品保存狀況", CONDITION_LABELS[listing.product.condition]);
}
