export const SHOPEE_URLS = {
  sellerCenter: "https://seller.shopee.tw/",
  newProduct: "https://seller.shopee.tw/portal/product/new"
};

export const selectors = {
  productImagesAdd: "text=/新增圖片 \\(\\d+\\/9\\)/",
  titleInput: 'input[placeholder*="品牌名稱"]',
  gtinInput: 'input[placeholder="Input"]',
  noValidGtinText: "text=商品無有效的國際條碼",
  descriptionEditor: '[contenteditable="true"]',
  priceInput: 'input[placeholder="Input"]',
  stockInput: 'input[placeholder="Input"]',
  weightInput: 'input[placeholder="Input"]',
  packageWidthInput: 'input[placeholder="寬"]',
  packageLengthInput: 'input[placeholder="長"]',
  packageHeightInput: 'input[placeholder="高"]',
  saveAndPublishButton: "text=儲存並上架"
};

export const labels = {
  brand: "品牌",
  hasBSMI: "是否有BSMI字號",
  connectionType: "連接類型",
  condition: "商品保存狀況",
  dangerousGoods: "禁運品"
};
