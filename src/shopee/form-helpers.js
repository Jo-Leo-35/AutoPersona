/**
 * Shopee uses custom dropdowns heavily. This helper keeps the intent readable
 * while allowing selector details to evolve in one place.
 *
 * @param {import("playwright").Page} page
 * @param {string} label
 * @param {string} option
 */
export async function chooseDropdownOption(page, label, option) {
  const labelNode = page.getByText(label, { exact: true }).first();
  await labelNode.scrollIntoViewIfNeeded();
  const container = labelNode.locator("xpath=ancestor::*[contains(@class, 'eds-form-item') or contains(@class, 'product-edit')][1]");

  if ((await container.count()) > 0) {
    await container.first().click();
  } else {
    await labelNode.click();
  }

  await page.getByText(option, { exact: true }).last().click();
}

/**
 * @param {import("playwright").Page} page
 * @param {string} text
 */
export async function clickTextIfVisible(page, text) {
  const target = page.getByText(text, { exact: true });
  if (await target.first().isVisible().catch(() => false)) {
    await target.first().click();
    return true;
  }
  return false;
}
