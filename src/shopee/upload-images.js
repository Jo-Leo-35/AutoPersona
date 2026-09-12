import path from "node:path";
import { selectors } from "./selectors.js";

/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * @param {import("playwright").Page} page
 * @param {string[]} imagePaths
 * @param {{ baseDir: string }} options
 */
export async function uploadImages(page, imagePaths, options) {
  const files = imagePaths.map((imagePath) =>
    path.isAbsolute(imagePath) ? imagePath : path.resolve(options.baseDir, imagePath)
  );

  for (const file of files) {
    const chooserPromise = page.waitForEvent("filechooser");
    await page.locator(selectors.productImagesAdd).first().click();
    const chooser = await chooserPromise;
    await chooser.setFiles(file);
    await page.waitForLoadState("networkidle").catch(() => {});
  }
}
