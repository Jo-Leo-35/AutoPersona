#!/usr/bin/env python3
"""Prepare the versioned Persona handoff locally, without API/config/browser I/O.

Run from any directory; paths in the input resolve from the AutoPersona root.
This adapter reuses the canonical Python normalizer and question collector.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autopersona_py.planner import normalize_listing
from autopersona_py.schema import FIELDS, RESEARCH_PATTERN, get_path, collect_questions

VERSION = "1.0.0"
CONTEXT_PATHS = {
    "persona.audience", "persona.useCases", "persona.painPoints",
    "persona.positioning", "persona.competitors", "content.highlights", "content.keywords",
}
MEDIA_CONFIRMATION_PATHS = {"media.confirmedProductImages", "media.uploadAuthorized"}


def prepare_contract(raw, root=ROOT):
    """Return a normalized listing and browser guidance, never publication authority.

    JSON Schema is provided for producer-side validation. Here the version/envelope
    is checked before delegating field coercion and consistency to normalize_listing.
    """
    if not isinstance(raw, dict) or raw.get("schemaVersion") != VERSION:
        raise ValueError("schemaVersion 必須是 " + VERSION + "；其他版本請先對映。")
    if not isinstance(raw.get("exampleId"), str) or not raw["exampleId"].strip():
        raise ValueError("exampleId 必須是非空文字。")
    if not isinstance(raw.get("listing"), dict):
        raise ValueError("listing 必須是 JSON 物件。")
    if set(raw) - {"schemaVersion", "exampleId", "listing"}:
        raise ValueError("契約外層只接受 schemaVersion、exampleId、listing。")
    listing = normalize_listing(raw)
    listing["automation"] = {"mode": "draft_only", "allowPublish": False}
    questions = collect_questions(listing, root)
    question_by_path = {item["path"]: item for item in questions}
    entries = []
    for path, (_kind, label, required, _options) in FIELDS.items():
        value = get_path(listing, path)
        known = value is not None and value != "" and value != []
        status = "ready" if known else "needs_answer"
        reason = "已提供，可在實際頁面找到對應控制項後填入。" if known else "未知值保留空白，不自動補造。"
        fillable = known
        if path in CONTEXT_PATHS:
            status, fillable = "copy_context", False
            reason = "文案來源；不視為賣家頁面的獨立欄位。"
        elif path in MEDIA_CONFIRMATION_PATHS:
            status, fillable = "local_control", False
            reason = "本機確認資訊；不是賣家表單欄位，也不能從參考圖片推定。"
        elif path in ("media.imagePaths", "media.videoPath"):
            authorized = listing["media"]["uploadAuthorized"] is True
            identified = listing["media"]["confirmedProductImages"] is True
            reference_only = listing["media"]["referenceOnly"] is True
            fillable = bool(known and authorized and identified and not reference_only)
            status = "ready" if fillable else "withheld"
            reason = "檔案、商品身分與本回合上傳授權均已確認。" if fillable else "僅供參考或尚未獲本回合上傳確認；先不選取檔案。"
        elif path == "product.categoryPath":
            status, fillable = "needs_page_choice", False
            reason = "先核對實際賣家頁面的分類選項；已提供路徑也不當成現行網站證據。"
        if path in question_by_path and status == "ready":
            status, fillable = "needs_answer", False
            reason = question_by_path[path]["reason"]
        entries.append({"path": path, "label": label, "value": deepcopy(value),
                        "status": status, "fillable": fillable, "required": required,
                        "reason": reason})
    # The browser handoff contains allowed form paths only, no research payload.
    field_map = {"schemaVersion": VERSION, "exampleId": raw["exampleId"],
                 "destination": "shopee_seller_draft", "researchExcluded": True,
                 "allowPublish": False, "entries": entries}
    public_copy = {name: listing[name] for name in ("product", "persona", "content")}
    if RESEARCH_PATTERN.search(json.dumps(public_copy, ensure_ascii=False)):
        raise ValueError("內部研究資料不得進入商品文案。")
    return {"schemaVersion": VERSION, "exampleId": raw["exampleId"],
            "listing": listing, "questions": questions, "fieldMap": field_map,
            "processing": {"mode": "local_normalization", "apiCalled": False,
                           "configRead": False, "browserOperated": False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path,
                        help="Write normalized.v1.json, field-map.v1.json, questions.v1.json")
    args = parser.parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        prepared = prepare_contract(raw)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.output_dir is None:
        print(json.dumps(prepared, ensure_ascii=False, indent=2, allow_nan=False))
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "normalized.v1.json": {key: prepared[key] for key in ("schemaVersion", "exampleId", "listing")},
        "field-map.v1.json": prepared["fieldMap"],
        "questions.v1.json": {"schemaVersion": VERSION, "questions": prepared["questions"]},
    }
    for name, payload in outputs.items():
        (args.output_dir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"outputs": list(outputs), "processing": prepared["processing"],
                      "fillablePaths": [entry["path"] for entry in prepared["fieldMap"]["entries"] if entry["fillable"]],
                      "questionCount": len(prepared["questions"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
