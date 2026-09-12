# AutoPersona Workflow

AutoPersona is designed for sellers who want fast listing creation without learning Shopee's full product form.

## Main Flow

1. Create a product folder.

   ```text
   products/my-product/
     product.json
     images/
   ```

2. Add product images to `images/`.

3. Fill only the facts the seller already knows in `product.json`.

4. Run draft mode.

   ```bash
   node src/cli.js draft products/my-product/product.json
   ```

5. Review generated copy, warnings, and blocking errors.

6. Fix missing data.

7. Run fill mode.

   ```bash
   node src/cli.js fill products/my-product/product.json
   ```

8. AutoPersona opens Shopee and fills the form.

9. Seller reviews the form manually.

10. Seller decides whether to publish.

## What the Seller Must Provide

- Product title or reference title
- Images
- Category
- Brand when known
- Model when known
- Price
- Stock
- Weight
- Package width, length, height
- Condition: new or used
- BSMI/NCC/GTIN facts when applicable
- Warranty and package contents when known

## What AutoPersona Can Generate

- Shopee product description
- Positioning copy
- Highlights
- Keywords
- Review summary
- Missing-data checklist

## What AutoPersona Must Not Guess

- Full SKU variant
- BSMI number
- NCC number
- GTIN
- Warranty
- Package contents
- Wireless frequency
- Battery life
- Whether a receiver or accessory is included

## Human Review Gate

The publish button is never clicked by automation. `automation.allowPublish` must be `false`.

The final output should always answer:

- What was filled?
- What was skipped?
- What is missing?
- What must a human verify?

## Codex / Adrian Assist Mode

In `codex_assist` mode, the same `product.json` can be handed to Codex or another operator.

The agent should:

1. Read the schema.
2. Run validation.
3. Generate or review copy.
4. Fill only fields that are explicit in the JSON.
5. Stop before publishing.
6. Report a final review summary.

