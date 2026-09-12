#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { buildPersonaPrompt } from "./persona/prompt-builder.js";
import { createDraft, fillShopeeForm } from "./flows/create-listing.js";
import { validateListing } from "./schema/validator.js";

const [, , command = "draft", productFileArg = "products/example-shure-sm58/product.json"] = process.argv;

function usage() {
  console.log([
    "AutoPersona",
    "",
    "Usage:",
    "  node src/cli.js draft <product.json>",
    "  node src/cli.js validate <product.json>",
    "  node src/cli.js prompt <product.json>",
    "  node src/cli.js fill <product.json>",
    "",
    "Commands:",
    "  draft     Generate local Persona copy and print review summary.",
    "  validate  Validate product JSON only.",
    "  prompt    Print the Persona Engine prompt.",
    "  fill      Open Shopee and fill the form. Never publishes."
  ].join("\n"));
}

/**
 * @param {string} filePath
 */
function loadListing(filePath) {
  const resolved = path.resolve(filePath);
  const raw = fs.readFileSync(resolved, "utf8");
  return { listing: JSON.parse(raw), productFilePath: resolved };
}

function printIssues(title, issues) {
  console.log(`${title}: ${issues.length}`);
  issues.forEach((issue) => console.log(`- ${issue.path}: ${issue.message}`));
}

async function main() {
  if (command === "help" || command === "--help" || command === "-h") {
    usage();
    return;
  }

  const { listing, productFilePath } = loadListing(productFileArg);
  const baseDir = path.dirname(productFilePath);

  if (command === "validate") {
    const validation = validateListing(listing, { baseDir });
    printIssues("Errors", validation.errors);
    printIssues("Warnings", validation.warnings);
    process.exitCode = validation.errors.length > 0 ? 1 : 0;
    return;
  }

  if (command === "prompt") {
    console.log(buildPersonaPrompt(listing));
    return;
  }

  if (command === "draft" || command === "review") {
    const draft = createDraft(listing, { productFilePath });
    console.log(draft.summary);
    console.log("");
    console.log("Generated Description:");
    console.log(draft.listing.content.description);
    process.exitCode = draft.validation.errors.length > 0 ? 1 : 0;
    return;
  }

  if (command === "fill") {
    const result = await fillShopeeForm(listing, { productFilePath });
    console.log(result.summary);
    if (result.skipped) {
      console.log("");
      console.log(`Skipped: ${result.reason}`);
      process.exitCode = 1;
    } else {
      console.log("");
      console.log(result.note);
    }
    return;
  }

  usage();
  process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
