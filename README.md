# AutoPersona

AutoPersona is a semi-automated Shopee listing assistant. It turns structured product data and persona positioning into Shopee-ready copy, validates risky or missing fields, and uses Playwright to fill the seller-center form.

It does **not** auto-publish listings. The default workflow stops before `儲存並上架` so a human can review pricing, compliance, logistics, images, and copy.

## Why This Exists

Shopee listing is repetitive, but some fields are too risky to guess:

- BSMI / NCC
- GTIN
- warranty
- package contents
- exact model or SKU
- wireless frequency
- logistics size and weight

AutoPersona separates those concerns:

- Persona Engine generates copy and positioning.
- Validator blocks or warns about missing listing data.
- Playwright fills only the fields that are explicitly provided.
- The seller makes the final publishing decision.

## Quick Start

```bash
npm install
npm run draft
```

If you are using the bundled Codex runtime, this also works without installing:

```bash
/Users/etahn/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node src/cli.js draft products/example-shure-sm58/product.json
```

## Product Folder

Create one folder per product:

```text
products/
  example-shure-sm58/
    product.json
    images/
      shure-sm58-main.png
      shure-sm58-box.png
```

Run:

```bash
node src/cli.js draft products/example-shure-sm58/product.json
node src/cli.js validate products/example-shure-sm58/product.json
node src/cli.js fill products/example-shure-sm58/product.json
```

## Workflow

1. Prepare product data and images.
2. Run `draft` to generate persona-based Shopee copy.
3. Review validation warnings and missing fields.
4. Run `fill` to open Shopee Seller Center and fill the form.
5. Review the Shopee form manually.
6. Publish manually only after confirming every field.

## Automation Modes

- `draft_only`: generate copy and review summary only.
- `fill_form`: open Shopee and fill the form.
- `review_only`: summarize a prepared listing.
- `codex_assist`: hand the structured product data to Codex or another operator.

`automation.allowPublish` must always be `false`.

## Schema Overview

```js
{
  "product": {
    "title": "Shure SM58 手持麥克風｜社區志工・活動主持・導覽宣導｜輕巧好攜帶",
    "categoryPath": ["影音", "麥克風"],
    "brand": "SHURE 舒爾",
    "model": "SM58",
    "condition": "used",
    "noValidGtin": false
  },
  "persona": {
    "audience": ["社區志工", "活動主持"],
    "useCases": ["社區活動", "志工宣導", "社區導覽"],
    "painPoints": ["需要移動", "臨時活動需要快速使用"],
    "positioning": "方便攜帶、活動現場快速使用"
  },
  "compliance": {
    "hasBSMI": false,
    "hasNCC": false
  },
  "sales": {
    "price": 7999,
    "stock": 1
  },
  "shipping": {
    "weightKg": 0.3,
    "packageSizeCm": {
      "width": 30,
      "length": 30,
      "height": 30
    },
    "dangerousGoods": false
  },
  "media": {
    "imagePaths": ["images/shure-sm58-main.png"]
  },
  "automation": {
    "mode": "draft_only",
    "allowPublish": false
  }
}
```

## Persona Engine Integration

The first version ships with a local deterministic Persona Engine stub. Later, replace `src/persona/persona-engine.js` with an API client that sends:

- product title
- target audience
- use cases
- pain points
- competitors
- positioning notes

The engine should return:

- title suggestions
- Shopee description
- highlights
- keywords

## Safety Rules

AutoPersona must not infer or fabricate:

- complete SKU variant
- BSMI/NCC numbers
- GTIN
- warranty
- package contents
- frequency
- battery life
- receiver inclusion
- official product certification

Missing fields are shown as errors or warnings.

## Shopee Filling

Shopee selectors are centralized in `src/shopee/selectors.js`. The Playwright modules are intentionally small so Shopee UI changes can be repaired in one place.

The fill flow is:

```text
openSellerCenter
fillBasicInfo
uploadImages
fillAttributes
fillDescription
fillSales
fillShipping
reviewSummary
```

The fill command currently prepares the flow and stops before publishing. It never clicks `儲存並上架`.

