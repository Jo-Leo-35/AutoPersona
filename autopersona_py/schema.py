"""Listing form contract and explicit follow-up answers (Python 3.9+).

Unknown scalar facts remain None. Validation returns questions so an incomplete
listing can still be reviewed and partially filled; it does not authorize publish.
"""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List


# These labels describe audience research, not evidence about the listed SKU.
RESEARCH_PATTERN = re.compile(
    r"verified\s*purchase|missed\s*buyer|\d+\s*(?:則|筆|條)\s*(?:命中|評論|評價)|"
    r"(?:驗證|認證|已驗證)購買(?:者)?(?:評論|評價)?|\d+\s+(?:matched\s+)?reviews?", re.I)
STOREFRONT_PATHS = {"product.title", "persona.audience", "persona.useCases",
                    "persona.painPoints", "persona.positioning", "persona.competitors",
                    "content.description", "content.highlights", "content.keywords"}


def empty_listing() -> Dict[str, Any]:
    return {
        "product": {"title": None, "categoryPath": [], "brand": None,
                    "model": None, "condition": None, "gtin": None,
                    "noValidGtin": None},
        "persona": {"audience": [], "useCases": [], "painPoints": [],
                    "positioning": None, "competitors": []},
        "content": {"description": None, "highlights": [], "keywords": []},
        "compliance": {"hasBSMI": None, "hasNCC": None, "bsmiNumber": None,
                       "nccNumber": None, "warrantyPeriod": None,
                       "warrantyType": None, "packageContents": None,
                       "connectionType": None, "headphoneType": None},
        "sales": {"price": None, "stock": None, "minPurchaseQty": None},
        "shipping": {"weightKg": None,
                     "packageSizeCm": {"width": None, "length": None, "height": None},
                     "dangerousGoods": None},
        "media": {"imagePaths": [], "videoPath": None,
                  "referenceImagePaths": [], "referenceOnly": None,
                  "confirmedProductImages": None, "uploadAuthorized": None},
        "research": {"internalOnly": True},
        "automation": {"mode": "draft_only", "allowPublish": False},
    }


# path: (input type, human label, required, options)
FIELDS = {
    "product.title": ("text", "商品名稱", True, None),
    "product.categoryPath": ("array", "商品分類路徑", True, None),
    "product.brand": ("text", "品牌（確認後填寫）", False, None),
    "product.model": ("text", "完整型號（確認後填寫）", False, None),
    "product.condition": ("select", "商品狀況", True, ["new", "used"]),
    "product.gtin": ("text", "GTIN 商品條碼", False, None),
    "product.noValidGtin": ("boolean", "已確認沒有有效 GTIN", False, None),
    "sales.price": ("number", "售價（TWD）", True, None),
    "sales.stock": ("integer", "庫存數量", True, None),
    "sales.minPurchaseQty": ("integer", "最低購買數量", False, None),
    "shipping.weightKg": ("number", "包裹重量（kg）", True, None),
    "shipping.packageSizeCm.width": ("number", "包裹寬度（cm）", True, None),
    "shipping.packageSizeCm.length": ("number", "包裹長度（cm）", True, None),
    "shipping.packageSizeCm.height": ("number", "包裹高度（cm）", True, None),
    "shipping.dangerousGoods": ("boolean", "是否為危險物品", True, None),
    "compliance.hasBSMI": ("boolean", "是否具有 BSMI 認證", True, None),
    "compliance.hasNCC": ("boolean", "是否具有 NCC 認證", True, None),
    "compliance.bsmiNumber": ("text", "BSMI 認證字號", False, None),
    "compliance.nccNumber": ("text", "NCC 認證字號", False, None),
    "compliance.warrantyPeriod": ("text", "保固期限", False, None),
    "compliance.warrantyType": ("text", "保固方式", False, None),
    "compliance.packageContents": ("text", "實際包裝內容", False, None),
    "compliance.connectionType": ("select", "連線方式", False, ["wired", "wireless"]),
    "compliance.headphoneType": ("text", "耳機類型（依實際頁面選項）", False, None),
    "media.imagePaths": ("array", "商品圖片路徑（每行一個）", True, None),
    "media.confirmedProductImages": ("boolean", "圖片已確認為本次販售商品", False, None),
    "media.uploadAuthorized": ("boolean", "使用者已指定上傳這些圖片", False, None),
    "media.videoPath": ("text", "商品影片路徑", False, None),
    "persona.audience": ("array", "目標客群", False, None),
    "persona.useCases": ("array", "使用情境", False, None),
    "persona.painPoints": ("array", "購買者需求", False, None),
    "persona.positioning": ("text", "商品定位", False, None),
    "persona.competitors": ("array", "比較對象", False, None),
    "content.description": ("text", "商品描述", False, None),
    "content.highlights": ("array", "文案重點", False, None),
    "content.keywords": ("array", "搜尋關鍵字", False, None),
}


def get_path(data: Dict[str, Any], path: str) -> Any:
    value = data
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def set_path(data: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(data.get(part), dict):
            data[part] = {}
        data = data[part]
    data[parts[-1]] = value


def coerce_value(path: str, value: Any) -> Any:
    """Coerce form text without treating bools as numbers or 'false' as True."""
    if path not in FIELDS:
        raise ValueError("不允許修改欄位：" + str(path))
    kind, label, _required, options = FIELDS[path]
    if value is None or (isinstance(value, str) and not value.strip()):
        return [] if kind == "array" else None
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "yes", "是", "有"):
                return True
            if normalized in ("false", "no", "否", "無", "沒有"):
                return False
        raise ValueError(label + " 必須明確填寫 true 或 false。")
    if kind in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError(label + " 必須是有效數字。")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            raise ValueError(label + " 必須是有效數字。") from None
        if not number.is_finite() or not math.isfinite(float(number)):
            raise ValueError(label + " 必須是有限數字。")
        if kind == "integer" and number != number.to_integral_value():
            raise ValueError(label + " 必須是整數。")
        minimum = Decimal("0") if path == "sales.stock" else Decimal("0.000000000001")
        if number < minimum:
            raise ValueError(label + (" 不得小於 0。" if minimum == 0 else " 必須大於 0。"))
        return int(number) if kind == "integer" else float(number)
    if kind == "array":
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    value = json.loads(value)
                except (ValueError, TypeError):
                    raise ValueError(label + " 的 JSON 陣列格式無效。") from None
            else:
                # Image paths may contain spaces or commas; preserve both.
                pattern = r"[\n>＞]+" if path == "product.categoryPath" else r"[\n]+"
                value = re.split(pattern, value)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(label + " 必須是文字陣列或每行一項的文字。")
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))
    if not isinstance(value, str):
        raise ValueError(label + " 必須是文字。")
    value = value.strip()
    if options is not None:
        value = {"全新": "new", "二手": "used"}.get(value, value)
        if value not in options:
            raise ValueError(label + " 必須是 " + " / ".join(options) + "。")
    return value


def validate_consistency(listing: Dict[str, Any]) -> None:
    """Use the same cross-field validation for JSON imports and follow-ups."""
    if get_path(listing, "product.noValidGtin") is True and get_path(listing, "product.gtin"):
        raise ValueError("已填 GTIN 時，不能同時確認沒有有效 GTIN。")
    for flag, number in (("hasBSMI", "bsmiNumber"), ("hasNCC", "nccNumber")):
        if get_path(listing, "compliance." + flag) is False and get_path(listing, "compliance." + number):
            raise ValueError("認證狀態與認證字號不一致，請確認後一併修正。")


def apply_answers(listing: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
    """Apply only allowlisted dotted form paths, atomically, to a deep copy.

    Missing/blank answers retain an unknown value. Invalid values reject the whole
    batch. Research, credentials and automation controls are never answer fields.
    """
    if not isinstance(listing, dict) or not isinstance(answers, dict):
        raise ValueError("listing 與 answers 必須是 JSON 物件。")
    clean = {}
    for path, value in answers.items():
        if not isinstance(path, str) or path not in FIELDS:
            raise ValueError("answers 包含不允許修改的欄位。")
        clean[path] = coerce_value(path, value)
        if path in STOREFRONT_PATHS and RESEARCH_PATTERN.search(json.dumps(clean[path], ensure_ascii=False)):
            raise ValueError("商品文案不得包含 Persona 研究標籤或評論命中數；請保留在內部研究。")
    result = deepcopy(listing)
    for path, value in clean.items():
        set_path(result, path, value)
    validate_consistency(result)
    if not isinstance(result.get("automation"), dict):
        result["automation"] = {"mode": "draft_only"}
    result["automation"]["allowPublish"] = False
    return result


def collect_questions(listing: Dict[str, Any], root: Path) -> List[Dict[str, Any]]:
    """Return missing/invalid field questions; required means needed to complete.

    Callers may fill known fields first. Photo identity confirmation is separate
    from the user's authorization to upload supplied images.
    """
    if not isinstance(listing, dict):
        raise ValueError("listing 必須是 JSON 物件。")
    questions = []
    skip = {"persona.audience", "persona.useCases", "persona.painPoints",
            "persona.positioning", "persona.competitors", "content.description",
            "content.highlights", "content.keywords", "media.videoPath",
            "sales.minPurchaseQty", "compliance.warrantyType", "compliance.connectionType",
            "media.uploadAuthorized", "compliance.headphoneType"}
    for path, (kind, label, required, options) in FIELDS.items():
        if path in skip:
            continue
        value = get_path(listing, path)
        if path == "product.gtin" and get_path(listing, "product.noValidGtin") is True:
            continue
        if path == "product.noValidGtin" and get_path(listing, "product.gtin"):
            continue
        if path in ("compliance.bsmiNumber", "compliance.nccNumber"):
            flag = "compliance.hasBSMI" if path.endswith("bsmiNumber") else "compliance.hasNCC"
            if get_path(listing, flag) is not True:
                continue
            required = True
        reason = "尚未提供，請依實際商品資料確認；不會自動推測。"
        missing = value is None or value == "" or value == []
        if not missing:
            try:
                normalized = coerce_value(path, value)
                # Persisted JSON must contain actual booleans and numbers.
                if kind == "boolean" and not isinstance(value, bool):
                    raise ValueError()
                if kind in ("number", "integer") and (isinstance(value, bool) or not isinstance(value, (int, float))):
                    raise ValueError()
                if normalized is None or normalized == "" or normalized == []:
                    raise ValueError()
            except ValueError:
                missing = True
                reason = "欄位值或格式無效，請確認後重新填寫。"
        if path == "product.title" and isinstance(value, str) and RESEARCH_PATTERN.search(value):
            missing = True
            reason = "商品名稱混入內部研究標籤，請提供實際商品名稱。"
        if path == "media.imagePaths" and isinstance(value, list) and value:
            for item in value:
                if not isinstance(item, str):
                    continue
                file_path = Path(item).expanduser()
                if not file_path.is_absolute():
                    file_path = Path(root) / file_path
                if not file_path.is_file():
                    missing = True
                    reason = "圖片路徑不存在或不是檔案，請提供可用的本機圖片路徑。"
                    break
        if path == "media.confirmedProductImages" and value is not True:
            missing = True
            reason = "使用者指定上傳與商品身分核對是兩件事；請在發布前確認圖片與實際販售商品一致。"
        if path == "compliance.warrantyPeriod" and get_path(listing, "compliance.warrantyType"):
            continue
        if missing:
            question = {"path": path, "label": label, "type": kind,
                        "required": required, "reason": reason}
            if options:
                question["options"] = list(options)
            questions.append(question)
    return questions


def validate_listing(listing: Dict[str, Any], root: Path) -> List[Dict[str, Any]]:
    """Compatibility name: same question-list contract as collect_questions."""
    return collect_questions(listing, root)
