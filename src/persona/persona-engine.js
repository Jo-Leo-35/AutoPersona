/**
 * @typedef {import("../schema/listing.schema.js").ListingSchema} ListingSchema
 */

/**
 * Local deterministic Persona Engine stub.
 * Replace this file with a real API client when the Persona Engine endpoint is ready.
 *
 * @param {ListingSchema} listing
 * @returns {{ description: string, highlights: string[], keywords: string[] }}
 */
export function generateListingContent(listing) {
  const productName = listing.product.model
    ? `${listing.product.brand ?? ""} ${listing.product.model}`.trim()
    : listing.product.title;

  const audience = listing.persona.audience.join("、");
  const useCases = listing.persona.useCases.join("、");
  const highlights = [
    "手持式設計，方便活動現場移動與攜帶",
    "適合臨時活動、宣導、主持、導覽與現場引導",
    "操作方式直覺，適合一般活動與志工場景"
  ];

  const scenarioLines = listing.persona.useCases.map((item) => `✓ ${item}`).join("\n");

  const description = [
    "社區活動需要的，不一定是一套複雜的音響設備。",
    "",
    `對${audience || "需要在現場移動的使用者"}來說，`,
    "好拿、好帶、需要使用時可以快速拿起來，",
    "往往比複雜的功能更重要。",
    "",
    `這款 ${productName} 手持麥克風，`,
    `適合${useCases || "活動現場說明"}等使用情境。`,
    "",
    "【適合使用情境】",
    "",
    scenarioLines,
    "",
    "【特色】",
    "",
    highlights.join("\n\n"),
    "",
    "簡潔的手持操作方式，",
    "適合社區活動、志工與一般活動使用。"
  ].join("\n");

  const keywords = [
    listing.product.brand,
    listing.product.model,
    ...listing.persona.audience,
    ...listing.persona.useCases,
    "手持麥克風",
    "活動主持",
    "社區導覽"
  ].filter(Boolean);

  return { description, highlights, keywords };
}
