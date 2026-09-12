#!/usr/bin/env python3
"""Rebuild this product handoff with the existing local Persona contract.

Reads no environment/configuration and performs no network or browser operations.
The source Persona JSON stays portable; browser observations stay separate.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "examples/browser-demo"))
from prepare_contract import prepare_contract


def read(name):
    return json.loads((PRODUCT / name).read_text(encoding="utf-8"))


def save(name, payload):
    (PRODUCT / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def build():
    raw = read("persona-input.v1.json")
    facts = read("product-facts.json")
    observed = read("observed-site-state.json")
    prepared = prepare_contract(raw, ROOT)
    listing = prepared["listing"]
    field_map = prepared["fieldMap"]
    observed_fields = observed["observedFields"]
    for entry in field_map["entries"]:
        if entry["path"] in observed_fields:
            observation = observed_fields[entry["path"]]
            reason = (
                "既有頁面值已讀回，保留原值；觀測資料不轉為本輪賣家確認答案。"
                if observation["sourceType"] == "current_browser_observed"
                else "歷史頁面曾有此值，核對並保留現場值；不從歷史觀測補成確認答案。"
            )
            entry.update(
                status="retain_observed", fillable=False,
                observedValue=deepcopy(observation["value"]),
                reason=reason,
            )
    field_map["blockers"] = []
    question_items = []
    for question in prepared["questions"]:
        question = deepcopy(question)
        path = question["path"]
        if path in observed_fields:
            question.update(
                observedValue=deepcopy(observed_fields[path]["value"]),
                askWhen="creating_new_listing_or_observed_value_changes",
                reason="目前既有頁面已有值，維持現場值；新建商品或變更時再確認。",
            )
        elif path.startswith("media."):
            question.update(
                askWhen="adding_or_replacing_existing_images",
                reason="現場既有商品保留 2 張圖片；本輪沒有新增或替換圖片操作。",
            )
        else:
            question["askWhen"] = "required_by_current_page_or_explicit_update"
        question_items.append(question)
    save("listing.v1.json", {key: prepared[key] for key in ("schemaVersion", "exampleId", "listing")})
    save("field-map.v1.json", field_map)
    save("questions.v1.json", {
        "schemaVersion": "1.0.0", "questions": question_items, "blockers": [],
        "alreadyObservedOnExistingPage": observed_fields,
        "instruction": "先完成可填欄位；僅於實站要求缺少資料時集中提問。既有價格、庫存、圖片及商品狀況保留。",
    })
    save("research.json", listing["research"])
    save("browser-handoff.json", {
        "schemaVersion": "1.0.0", "exampleId": raw["exampleId"],
        "existingProductId": observed["existingProductId"],
        "title": listing["product"]["title"],
        "description": listing["content"]["description"],
        "model": listing["product"]["model"],
        "compliance": listing["compliance"],
        "specifications": facts["specifications"],
        "certificationEarMapping": facts["certifications"]["ncc"],
        "sales": listing["sales"],
        "retainExistingPageValues": observed_fields,
        "imageAction": "retain_existing_images",
        "observedImageCount": observed["media"]["imageCount"],
        "imagePaths": [],
        "referenceImagePaths": listing["media"]["referenceImagePaths"],
        "pageAttributeSuggestions": [
            {"label": "品牌", "value": "JLab", "basis": "本輪使用者正式型號"},
            {"label": "耳機類型", "value": "開放式", "basis": "本輪使用者指定開放式商品"},
            {"label": "連接類型", "value": "無線", "basis": "本輪藍牙 5.3 規格"},
        ],
        "nccFormConstraint": observed["fieldMappings"]["compliance.nccNumber"],
        "leaveBlankUnlessPageRequires": ["保固", "GTIN", "物流重量與尺寸", "危險物品分類"],
        "researchExcluded": True, "blockers": [], "allowPublish": False,
        "processing": prepared["processing"],
    })
    for filename, content in (("title.txt", listing["product"]["title"]),
                              ("description.txt", listing["content"]["description"])):
        (PRODUCT / filename).write_text(content + "\n", encoding="utf-8")
    print(json.dumps({
        "exampleId": raw["exampleId"], "processing": prepared["processing"],
        "descriptionCharacters": len(listing["content"]["description"]),
        "questionCount": len(question_items),
        "observedValuesRetained": list(observed_fields),
    }, ensure_ascii=False))


if __name__ == "__main__":
    build()
