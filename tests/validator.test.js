import test from "node:test";
import assert from "node:assert/strict";
import { validateListing } from "../src/schema/validator.js";

const validListing = {
  product: {
    title: "Test Product",
    categoryPath: ["影音", "麥克風"],
    brand: "SHURE 舒爾",
    model: "SM58",
    condition: "used",
    noValidGtin: true
  },
  persona: {
    audience: ["社區志工"],
    useCases: ["社區活動"],
    painPoints: ["需要移動"],
    positioning: "方便攜帶"
  },
  compliance: {
    hasBSMI: false,
    hasNCC: false,
    warrantyPeriod: "未提供",
    packageContents: "未提供"
  },
  sales: {
    price: 7999,
    stock: 1
  },
  shipping: {
    weightKg: 0.3,
    packageSizeCm: {
      width: 30,
      length: 30,
      height: 30
    },
    dangerousGoods: false
  },
  media: {
    imagePaths: ["images/main.png"]
  },
  automation: {
    mode: "draft_only",
    allowPublish: false
  }
};

test("valid listing has no blocking errors", () => {
  const result = validateListing(validListing, { baseDir: process.cwd() });
  assert.equal(result.errors.length, 0);
});

test("allowPublish must remain false", () => {
  const result = validateListing({
    ...validListing,
    automation: {
      mode: "draft_only",
      allowPublish: true
    }
  });

  assert.equal(result.errors.length, 1);
  assert.equal(result.errors[0].path, "automation.allowPublish");
});

test("BSMI number is required when hasBSMI is true", () => {
  const result = validateListing({
    ...validListing,
    compliance: {
      ...validListing.compliance,
      hasBSMI: true
    }
  });

  assert.equal(result.errors.some((issue) => issue.path === "compliance.bsmiNumber"), true);
});
