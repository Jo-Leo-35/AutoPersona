"""A visible, persistent Playwright session with a separate publication gate.

All methods must run on the same worker thread. Page content is treated as data:
the only JavaScript evaluated is the fixed inspection/overlay code below.
"""

import copy
import hashlib
import json
import re
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse


_MISSING = object()
_FIELDS = {
    "product.title": ["商品名稱", "商品標題"],
    "product.categoryPath": ["商品分類", "類別"],
    "product.brand": ["品牌"],
    "product.model": ["型號"],
    "product.condition": ["商品保存狀況", "商品狀況"],
    "product.gtin": ["國際商品條碼", "國際條碼", "GTIN"],
    "product.noValidGtin": ["商品無有效的國際條碼"],
    "content.description": ["商品描述", "商品說明"],
    "sales.price": ["價格", "商品價格", "售價"],
    "sales.stock": ["庫存", "庫存數量", "商品數量"],
    "sales.minPurchaseQty": ["最低購買數量"],
    "shipping.weightKg": ["重量", "重量 (公斤)", "重量（公斤）", "重量(公斤)"],
    "shipping.packageSizeCm.width": ["寬", "寬度"],
    "shipping.packageSizeCm.length": ["長", "長度"],
    "shipping.packageSizeCm.height": ["高", "高度"],
    "shipping.dangerousGoods": ["禁運品", "危險物品"],
    "compliance.hasBSMI": ["是否有BSMI字號", "是否有 BSMI 字號"],
    "compliance.bsmiNumber": ["BSMI", "BSMI字號", "BSMI 字號"],
    "compliance.hasNCC": ["是否有NCC字號", "是否有 NCC 字號"],
    "compliance.nccNumber": ["NCC", "NCC字號", "NCC 字號"],
    "compliance.warrantyPeriod": ["保固期限", "保固期間"],
    "compliance.warrantyType": ["保固類型"],
    "compliance.packageContents": ["包裝內容", "商品包裝內容"],
    "compliance.connectionType": ["連接方式", "連接類型"],
    "compliance.headphoneType": ["耳機類型"],
    "media.imagePaths": ["商品圖片", "上傳商品圖片", "新增圖片"],
}

# Selectors observed on the real seller editor (2026-09-12), scoped to fields.
# These identifiers describe form attributes, never a particular product/value.
_SHOPEE_SCOPES = {
    "compliance.headphoneType": ".product-attribute-item-100519",
    "compliance.connectionType": ".product-attribute-item-100408",
    "compliance.nccNumber": ".product-attribute-item-100970",
    "compliance.bsmiNumber": ".product-attribute-item-100969",
    "sales.price": ".basic-price",
    "sales.stock": ".basic-stock",
}

_INSPECT_JS = r"""(fieldNames) => {
  const visible = el => !!(el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');
  const clean = text => String(text || '').replace(/\s+/g, ' ').trim().slice(0, 160);
  const groupOf = el => el.closest('[data-field-group], .shopee-form-item, .form-item, [role=group], fieldset');
  const ownLabel = el => el.labels?.length ? clean(Array.from(el.labels).map(x => x.innerText).join(' ')) : clean(el.getAttribute('aria-label'));
  const labelOf = el => {
    if (el.dataset.label) return clean(el.dataset.label);
    const group = groupOf(el);
    if (el.type === 'radio') {
      const groupLabel = group?.querySelector('legend, .shopee-form-item__label, [data-label]');
      if (groupLabel) return clean(groupLabel.innerText);
    }
    if (ownLabel(el)) return ownLabel(el);
    if (el.getAttribute('aria-label')) return clean(el.getAttribute('aria-label'));
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/);
    const labelled = ids.map(id => document.getElementById(id)?.innerText || '').join(' ');
    if (labelled.trim()) return clean(labelled);
    const label = group?.querySelector('label, .shopee-form-item__label, [data-label]');
    if (label) return clean(label.innerText);
    // Some observed seller fields have visible text but no associated <label>.
    // Only derive a label from a small ancestor with one visible control.
    const normalize = text => clean(text).replace(/[\s*＊:：]+/g, '').toLowerCase();
    for (let parent = el.parentElement, depth = 0; parent && depth < 5 && !['BODY','HTML'].includes(parent.tagName); parent = parent.parentElement, depth++) {
      const fields = Array.from(parent.querySelectorAll('input:not([type=hidden]), textarea, select, [contenteditable=true], [role=combobox]')).filter(visible);
      if (fields.length !== 1) continue;
      const labels = Array.from(parent.querySelectorAll('label, span, div, legend')).filter(visible)
        .map(x => clean(x.innerText)).filter(text => (fieldNames || []).some(name => normalize(name) === normalize(text)));
      if (new Set(labels.map(normalize)).size === 1) return labels[0];
    }
    return clean(el.getAttribute('placeholder') || '未命名欄位');
  };
  const controls = Array.from(document.querySelectorAll('input, textarea, select, [contenteditable=true], [role=combobox]'))
    .filter(el => visible(el) && !el.disabled && el.getAttribute('aria-disabled') !== 'true' &&
      !['password', 'hidden', 'submit', 'button'].includes(el.type) &&
      !(el.parentElement?.closest('[role=combobox]') && el.getAttribute('role') !== 'combobox'))
    .map((el, index) => {
      const group = groupOf(el);
      const label = labelOf(el);
      const type = el.getAttribute('role') === 'combobox' ? 'combobox' : (el.type || 'text');
      const radios = el.type === 'radio' ? Array.from((el.form || document).querySelectorAll('input[type=radio]'))
        .filter(x => el.name ? x.name === el.name : x === el) : [];
      const required = el.required || el.getAttribute('aria-required') === 'true' ||
        !!group?.querySelector('.required, .shopee-form-item__required') || /[*＊]/.test(label) || radios.some(x => x.required);
      const value = String(el.getAttribute('aria-valuetext') ?? el.value ?? el.innerText ?? '').trim();
      let empty = type === 'file' ? !el.files?.length : !value;
      if (type === 'combobox' && /^(請選擇|選擇|select\b|choose\b)/i.test(value)) empty = true;
      if (type === 'checkbox') empty = required && !el.checked;
      if (type === 'radio') {
        empty = !radios.some(x => x.checked);
      }
      return {
        index, path: el.dataset.field || '', label, type, required: !!required, empty,
        invalid: el.getAttribute('aria-invalid') === 'true' || (!!el.validity && !el.validity.valid),
        validation: clean(el.validationMessage || ''),
        options: el.tagName === 'SELECT' ? Array.from(el.options).filter(o => o.value && !o.disabled)
          .map(o => ({value: o.value, label: clean(o.textContent)})).slice(0, 60) :
          type === 'radio' ? radios.filter(x => !x.disabled).map(x => ({value: x.value, label: ownLabel(x)})) : []
      };
    });
  const errors = Array.from(document.querySelectorAll('[role=alert], .shopee-form-item__error, .field-error, [data-validation-error]'))
    .filter(visible).map(el => clean(el.innerText)).filter(Boolean).slice(0, 15);
  const step = Array.from(document.querySelectorAll('[data-step]')).find(visible)?.dataset.step || null;
  return {controls, errors, step};
}"""

_OVERLAY_JS = """text => {
  let el = document.getElementById('autopersona-agent-status');
  if (!el) {
    el = document.createElement('div'); el.id = 'autopersona-agent-status';
    el.style.cssText = 'position:fixed;bottom:18px;right:18px;z-index:2147483647;background:#102839;color:#fff;padding:12px 18px;border-radius:14px;font:600 14px system-ui;box-shadow:0 6px 24px #0003;max-width:380px;pointer-events:none';
    document.documentElement.appendChild(el);
  }
  el.textContent = 'AutoPersona · ' + text;
}"""

_SUBMISSION_SETTLED_JS = r"""({url, demo}) => {
  if (location.href !== url) return true;
  const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  if (demo) return Array.from(document.querySelectorAll('[data-testid="published-success"]')).some(visible);
  const notices = document.querySelectorAll('[role="alert"], [role="status"], .shopee-message, .shopee-notification, .shopee-toast, .shopee-modal__header');
  const result = /^(商品新增成功|新增商品成功|商品已成功上架|已成功上架|商品上架成功|更新成功|商品更新成功|儲存成功|保存成功|操作成功)[！!。]?$/;
  return Array.from(notices).some(el => visible(el) && result.test(el.innerText.trim())) ||
    Array.from(document.querySelectorAll('.shopee-form-item__error, .field-error, [data-validation-error]')).some(el => visible(el) && el.innerText.trim());
}"""


def _get(data: dict, path: str) -> Any:
    value = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return _MISSING
        value = value[key]
    return value


def _has_value(value: Any) -> bool:
    return value is not _MISSING and value is not None and value != "" and value != []


def _normal_label(label: str) -> str:
    return re.sub(r"[\s*＊:：]+", "", label).lower()


def _value_labels(value: Any) -> List[str]:
    text = str(value).lower() if isinstance(value, bool) else str(value)
    return [text] + {"new": ["全新"], "used": ["二手"], "wired": ["有線"],
                     "wireless": ["無線"], "true": ["是", "有"], "false": ["否", "無"]}.get(text, [])


def _same_value(path: str, actual: Any, expected: Any) -> bool:
    """Compare saved display values without treating a nonempty field as a match."""
    if not _has_value(expected) or actual is None:
        return False
    if isinstance(expected, list):
        expected = " / ".join(str(item) for item in expected)
    if isinstance(expected, bool):
        return actual is expected or str(actual).strip() in _value_labels(expected)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return Decimal(str(actual).strip()) == Decimal(str(expected))
        except InvalidOperation:
            return False
    clean = lambda value: " ".join(str(value).split()).casefold()
    return clean(actual) in {clean(label) for label in _value_labels(expected)}


def _path_for(control: dict) -> Optional[str]:
    path = control.get("path", "")
    if path in _FIELDS:
        return path
    label = _normal_label(control.get("label", ""))
    for path, labels in _FIELDS.items():
        if any(label == _normal_label(candidate) for candidate in labels):
            return path
    return None


def _question(path: str, label: str, reason: str, kind: str = "text", options=None) -> dict:
    result = {"path": path, "label": label, "type": kind, "required": True, "reason": reason}
    if options:
        result["options"] = options
    return result


class BrowserSession:
    """Owns one isolated, visible browser. Construct/use/close on one worker."""

    def __init__(self, root: Path, emit: Optional[Callable[[str, str], None]] = None,
                 *, headless: bool = False, slow_mo: int = 0, cdp_url: Optional[str] = None,
                 record_video_dir: Optional[Path] = None, profile_dir: Optional[Path] = None,
                 fullscreen: bool = False):
        self.root = Path(root).resolve()
        self.emit = emit or (lambda event, message: None)
        self.headless = headless
        self.slow_mo = slow_mo
        self.fullscreen = bool(fullscreen and not headless)
        # Attach only when the caller explicitly requests CDP. An environment
        # setting must never silently take over the everyday Chrome session.
        self.cdp_url = cdp_url
        self.record_video_dir = Path(record_video_dir).resolve() if record_video_dir else None
        # An override names the exact dedicated Chrome profile, not a parent.
        self.profile_dir = Path(profile_dir).expanduser().resolve() if profile_dir else None
        self._thread = None
        self._pw = None
        self.context = None
        self.page = None
        self.mode = "demo"
        self._listing = {}
        self._filled = []
        self._issues = []
        self._published = False
        self._publish_attempted = False
        self._last_step = None
        self._attached = False
        self._cdp_browser = None
        self._video = None
        self._video_file = None
        self._engine = None
        self._completion_evidence = None
        self._uploaded_paths = None
        self._product_id = None
        self._target_url = None
        self._readback_paths = []
        self._readback_verified = False
        self._preserved_images = False
        self._readback_mismatches = []
        self._locator_cache = {}
        self._retained_values = {}
        self._submission_action = None
        self._submission_url = None

    def _check_thread(self):
        current = threading.get_ident()
        if self._thread is None:
            self._thread = current
        if self._thread != current:
            raise RuntimeError("BrowserSession must be used from its dedicated worker thread")

    def _overlay(self, message: str):
        if self.page and not self.page.is_closed():
            try:
                self.page.evaluate(_OVERLAY_JS, message)
            except Exception:
                pass
        self.emit("browser", message)

    def _result(self, phase: str, questions=None, **extra) -> dict:
        browser = {"url": "", "title": "", "visible": not self.headless, "mode": self.mode,
                   "engine": self._engine, "completionVerified": self._published,
                   "completionEvidence": self._completion_evidence if self._published else None,
                   "operation": self._submission_action or ("update" if self._product_id else "create"),
                   "fullscreen": self.fullscreen, "slowMoMs": self.slow_mo,
                   "targetProductId": self._product_id, "readbackVerified": self._readback_verified,
                   "existingImagesPreserved": self._preserved_images,
                   "readbackFields": list(self._readback_paths) if self._readback_verified else [],
                   "readbackMismatchPaths": list(self._readback_mismatches),
                   "retainedExistingFields": sorted(self._retained_values)}
        if self.page and not self.page.is_closed():
            try:
                parsed = urlparse(self.page.url)
                # Login redirects can include authentication tokens in query strings.
                browser["url"] = parsed._replace(query="", fragment="").geturl()
                browser["title"] = self.page.title()[:160]
            except Exception:
                pass
        return {"phase": phase, "questions": questions or [], "filled": list(self._filled),
                "browser": browser, "publishAttempted": self._publish_attempted, **extra}

    def start(self, listing: dict, mode: str, base_url: str, *, product_id=None) -> dict:
        self._check_thread()
        if mode not in ("demo", "shopee"):
            raise ValueError("Browser mode must be demo or shopee")
        if product_id is not None and (mode != "shopee" or not isinstance(product_id, str)
                                       or re.fullmatch(r"[0-9]+", product_id) is None):
            raise ValueError("product_id must be a digits-only string in shopee mode")
        if self._publish_attempted:
            return self._result("published" if self._published else "awaiting_browser", message="本次上架已送出；請先核對結果，勿重複送出。")
        if self.context:
            self.close()
        self.mode = mode
        self._filled, self._issues = [], []
        self._last_step = None
        self._published = False
        self._completion_evidence = None
        self._uploaded_paths = None
        self._product_id = product_id
        self._readback_paths = []
        self._readback_verified = False
        self._preserved_images = False
        self._readback_mismatches = []
        self._locator_cache = {}
        self._retained_values = {}
        self._submission_action = None
        self._submission_url = None
        self._engine = None
        self._video, self._video_file = None, None
        self._listing = copy.deepcopy(listing)
        if mode == "demo":
            parsed = urlparse(base_url)
            if parsed.scheme not in ("http", "https") or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ValueError("The demo must use the local AutoPersona server")
            target = base_url.rstrip("/") + "/demo/seller"
        else:
            target = ("https://seller.shopee.tw/portal/product/" + product_id if product_id
                      else "https://seller.shopee.tw/portal/product/list/live/need_optimized")
        self._target_url = target
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            if mode == "shopee" and self.cdp_url:
                self._cdp_browser = self._pw.chromium.connect_over_cdp(self.cdp_url, timeout=10000)
                if not self._cdp_browser.contexts:
                    raise RuntimeError("The connected browser has no available context")
                self.context = self._cdp_browser.contexts[0]
                self._attached = True
                self._engine = "cdp"
                # Preserve every existing tab and product: this task owns a new tab.
                self.page = self.context.new_page()
            else:
                profile = self.profile_dir or self.root / ".autopersona" / "browser-profile" / mode
                profile.mkdir(parents=True, exist_ok=True)
                launch = {"user_data_dir": str(profile), "headless": self.headless,
                          "slow_mo": self.slow_mo, "viewport": {"width": 1320, "height": 960},
                          "accept_downloads": False}
                if self.fullscreen:
                    launch.update(args=["--start-fullscreen"], no_viewport=True)
                    launch.pop("viewport")
                if self.record_video_dir:
                    self.record_video_dir.mkdir(parents=True, exist_ok=True)
                    launch.update(record_video_dir=str(self.record_video_dir), record_video_size={"width": 1320, "height": 960})
                try:
                    self.context = self._pw.chromium.launch_persistent_context(channel="chrome", **launch)
                    self._engine = "chrome"
                except Exception:
                    # Different browser builds must not share mutable profile data.
                    fallback_profile = profile.with_name(profile.name + "-chromium")
                    fallback_profile.mkdir(parents=True, exist_ok=True)
                    launch["user_data_dir"] = str(fallback_profile)
                    self.emit("browser", "Chrome 啟動未完成，改用獨立 Chromium 視窗。")
                    self.context = self._pw.chromium.launch_persistent_context(**launch)
                    self._engine = "chromium"
                self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self._video = self.page.video
            self.page.set_default_timeout(1600)
            self.page.goto(target, wait_until="domcontentloaded", timeout=45000)
            self.page.bring_to_front()
            if mode == "shopee" and not product_id:
                self._overlay("已開啟指定的蝦皮商品清單；尋找新增商品入口")
                self._open_new_product()
            self._overlay("已開啟既有商品編輯頁，開始核對與更新資料" if product_id else "已開啟新增商品頁，開始填寫已提供的資料")
            return self.fill(listing)
        except Exception as error:
            # Exception messages can include entered values or URLs with secrets.
            self.emit("browser", "瀏覽器啟動或導頁失敗：" + type(error).__name__)
            if not self.context:
                self.close()
                message = "無法啟動瀏覽器。請確認已安裝 Chrome 或執行 playwright install chromium，再重試。"
            else:
                message = "瀏覽器已開啟，但商品頁尚未載入完成。請在視窗確認連線、登入與目前頁面，再按繼續。"
            return self._result("awaiting_browser", message=message, error=type(error).__name__)

    def _open_new_product(self):
        """Only enter creation from the requested list; never click an existing row."""
        if self._product_id or not self.page or "/portal/product/list/" not in self.page.url:
            return
        for role in ("button", "link"):
            entry = self.page.get_by_role(role, name=re.compile(r"^\s*[+＋]?\s*新增商品\s*$")).filter(visible=True)
            try:
                entry.first.wait_for(state="visible", timeout=4000)
                if entry.count() == 1:
                    entry.click()
                    self.page.wait_for_url(re.compile(r"/portal/product/new"), timeout=12000)
                    return
            except Exception:
                pass
        # The destination is a creation form, never an existing product editor.
        if "/portal/product/list/" in self.page.url:
            self.page.goto("https://seller.shopee.tw/portal/product/new", wait_until="domcontentloaded", timeout=45000)

    def _manual_gate(self) -> Optional[str]:
        if not self.page or self.page.is_closed():
            return "瀏覽器尚未開啟或視窗已關閉，請重新啟動。"
        if self.mode != "shopee":
            return None
        url = urlparse(self.page.url)
        if url.hostname != "seller.shopee.tw" or any(token in url.path.lower() for token in ("login", "signin", "captcha", "verify")):
            return "請在開啟的 Chrome 視窗完成蝦皮登入或驗證，再按繼續。"
        try:
            if self.page.locator('input[type="password"]:visible, iframe[src*="captcha"]:visible, [class*="captcha"]:visible').count():
                return "請在開啟的 Chrome 視窗手動完成登入／CAPTCHA，再按繼續。"
        except Exception:
            return "商品頁仍在載入，請確認頁面後按繼續。"
        expected_path = "/portal/product/" + (self._product_id or "new")
        if url.path.rstrip("/") != expected_path:
            return "請在此隔離視窗開啟指定商品的編輯頁後繼續；目前頁面不會被修改。" if self._product_id else "請在此隔離視窗開啟「新增商品」頁後繼續；目前頁面不會被修改。"
        return None

    def _scan(self) -> dict:
        return self.page.evaluate(_INSPECT_JS, [name for labels in _FIELDS.values() for name in labels])

    def _wait_for_editor(self):
        """Wait for the observed editor to hydrate; no unconditional pacing."""
        self.page.wait_for_function("""existing => {
          const visible = el => el && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
          const title = document.querySelector('input[placeholder*="品牌名稱"], input[data-field="product.title"]');
          if (!visible(title) || (existing && !title.value.trim())) return false;
          const busy = document.querySelectorAll('.shopee-loading-mask, [aria-busy="true"]');
          if (Array.from(busy).some(visible)) return false;
          return Array.from(document.querySelectorAll('.shopee-image-manager__itembox.can-drag img.shopee-image-manager__image'))
            .every(img => img.complete && img.naturalWidth > 0);
        }""", arg=bool(self._product_id), timeout=10000)
        self._locator_cache.clear()

    def _field_groups(self, label: str):
        normalized = re.escape(label.strip().strip("*＊:： "))
        groups = self.page.locator('[data-field-group], .shopee-form-item, .form-item, [role="group"], fieldset').filter(
            has=self.page.locator('label, legend, .shopee-form-item__label, [data-label]').filter(
                has_text=re.compile(r"^\s*[*＊]?\s*" + normalized + r"\s*[*＊:：]?\s*$"))).filter(visible=True)
        if groups.count() == 1:
            return groups
        label_node = self.page.get_by_text(re.compile(r"^\s*[*＊]?\s*" + normalized + r"\s*[*＊:：]?\s*$")).filter(visible=True)
        if label_node.count() == 1:
            derived = label_node.locator('xpath=ancestor::*[not(self::body) and not(self::html)][.//input or .//textarea or .//select or .//*[@contenteditable="true"] or .//*[@role="combobox"] or .//*[@aria-haspopup]][1]')
            if derived.count() == 1:
                return derived
        return groups

    def _locator(self, path: str, control: Optional[dict] = None):
        # Cache locators (not element handles) for this stable form layout. They
        # resolve fresh DOM nodes on every action. Clear on navigation/layout change.
        if path not in self._locator_cache:
            self._locator_cache[path] = self._resolve_locator(path, control)
        return self._locator_cache[path]

    def _resolve_locator(self, path: str, control: Optional[dict] = None):
        if self.mode == "demo":
            candidate = self.page.locator('[data-field="' + path + '"]')
            if candidate.count() == 1:
                return candidate
            return None
        if path == "product.title":
            candidate = self.page.locator('input[placeholder*="品牌名稱"]:visible')
            if candidate.count() == 1:
                return candidate
        if path in _SHOPEE_SCOPES:
            scope = self.page.locator(_SHOPEE_SCOPES[path]).filter(visible=True)
            if scope.count() == 1:
                if path in ("compliance.headphoneType", "compliance.connectionType"):
                    choice = scope.locator(".eds-selector").filter(visible=True)
                    if choice.count() == 1:
                        return choice
                candidate = scope.locator('input:not([type="hidden"]), textarea, select, [role="combobox"]').filter(visible=True)
                if candidate.count() == 1:
                    return candidate
        if path == "product.brand":
            candidate = self.page.locator(".product-brand-item .eds-selector").filter(visible=True)
            if candidate.count() == 1:
                return candidate
        if path == "content.description":
            candidate = self.page.locator('div.ql-editor[contenteditable="true"]').filter(visible=True)
            if candidate.count() == 1:
                return candidate
        if path == "media.imagePaths":
            candidate = self.page.locator('input[type="file"][accept="image/*"][multiple]')
            if candidate.count() == 1:
                return candidate
        names = ([control["label"]] if control and control.get("label") else []) + _FIELDS.get(path, [])
        for label in names:
            candidate = self.page.get_by_label(label, exact=True)
            if candidate.count() == 1 and (candidate.is_visible() or (path == "media.imagePaths" and candidate.get_attribute("type") == "file")):
                return candidate
            # Label-scoped fallbacks never index generic repeated placeholders.
            groups = self._field_groups(label)
            if groups.count() == 1:
                candidate = groups.locator('input:not([type="hidden"]), textarea, select, [contenteditable="true"], [role="combobox"]').filter(visible=True)
                if candidate.count() == 1:
                    return candidate
        if path == "product.title":
            candidate = self.page.locator('input[placeholder*="品牌名稱"]:visible')
            if candidate.count() == 1:
                return candidate
        if path.startswith("shipping.packageSizeCm."):
            for placeholder in _FIELDS[path]:
                candidate = self.page.get_by_placeholder(placeholder, exact=True).filter(visible=True)
                if candidate.count() == 1:
                    return candidate
        if path == "content.description":
            candidate = self.page.locator('[contenteditable="true"]:visible')
            if candidate.count() == 1:
                return candidate
        if path == "media.imagePaths":
            candidate = self.page.locator('.image-manager input[type="file"][accept*="image"], .image-uploader input[type="file"][accept*="image"]')
            if candidate.count() == 1:
                return candidate
        return None

    def _control_state(self, locator) -> dict:
        return locator.evaluate("""el => {
          let values;
          if (el.type === 'checkbox') values = [el.checked];
          else if (el.tagName === 'SELECT') values = [el.value, el.selectedOptions[0]?.textContent];
          else if (el.matches('.eds-selector')) values = [el.querySelector('.eds-selector__inner')?.innerText];
          else values = [el.getAttribute('aria-valuetext'), el.value, el.innerText].filter(x => x != null && x !== '');
          return {tag: el.tagName, type: el.type || '', role: el.getAttribute('role'),
            editable: el.isContentEditable, sellerChoice: el.matches('.eds-selector'),
            readonly: el.hasAttribute('readonly'), values};
        }""")

    def _control_matches(self, path: str, value: Any, locator=None) -> bool:
        locator = locator if locator is not None else self._locator(path)
        if locator is None:
            return False
        return any(_same_value(path, actual, value) for actual in self._control_state(locator)["values"])

    def _capture_existing_values(self):
        if not self._product_id:
            return
        for path in ("sales.price", "sales.stock"):
            if _has_value(_get(self._listing, path)) or path in self._retained_values:
                continue
            locator = self._locator(path)
            if locator is not None:
                values = self._control_state(locator)["values"]
                if values and _has_value(values[0]):
                    self._retained_values[path] = values[0]
        if self._images_present(self._locator("media.imagePaths")):
            self._preserved_images = True

    def _expected_value(self, path):
        value = _get(self._listing, path)
        return value if _has_value(value) else self._retained_values.get(path, value)

    def _verification_paths(self) -> List[str]:
        paths = ["product.title", "product.categoryPath", "content.description", "sales.price", "sales.stock", "media.imagePaths"]
        for path in ("product.brand", "compliance.headphoneType", "compliance.connectionType",
                     "compliance.nccNumber", "compliance.bsmiNumber"):
            if _has_value(_get(self._listing, path)):
                paths.append(path)
        # Verify provided optional fields only if the editor actually has them.
        # Weight/dimensions are not blanket requirements in all Shopee editors.
        for path in _FIELDS:
            if path not in paths and _has_value(_get(self._listing, path)) and self._locator(path) is not None:
                paths.append(path)
        return paths

    def _path_matches(self, path: str) -> bool:
        value = self._expected_value(path)
        if path == "product.categoryPath":
            return self._category_matches(value)
        if path == "media.imagePaths":
            return self._images_present(self._locator(path))
        return self._control_matches(path, value)

    def _category_matches(self, category: Any) -> bool:
        if not isinstance(category, list) or not category or not all(isinstance(part, str) and part for part in category):
            return False
        breadcrumb = re.compile(r"^\s*" + r"\s*[>›]\s*".join(re.escape(part) for part in category) + r"\s*$")
        exact = self.page.get_by_text(breadcrumb)
        if exact.count() == 1 and exact.is_visible():
            return True
        for label in ("商品分類", "類別"):
            groups = self._field_groups(label)
            if groups.count() == 1 and groups.is_visible():
                text = groups.inner_text()
                if re.search(r"\s*(?:[>›/]|\n)\s*".join(re.escape(part) for part in category), text):
                    return True
        return False

    def _choose_category(self, category: Any) -> bool:
        """Select only the supplied exact path inside the observed category dialog."""
        if not isinstance(category, list) or not category or not all(isinstance(part, str) and part for part in category):
            return False
        if self._category_matches(category):
            return True
        trigger = self.page.get_by_text("請選擇商品分類", exact=True)
        if trigger.count() != 1 or not trigger.is_visible():
            return False
        trigger.click()
        heading = self.page.get_by_text("編輯分類", exact=True)
        heading.wait_for(state="visible", timeout=4000)
        if heading.count() != 1:
            return False
        scope = self.page.get_by_role("dialog").filter(has=heading)
        if scope.count() != 1:
            # The site may omit dialog semantics. Derive the smallest container
            # holding this observed heading and its observed Confirm button.
            scope = heading.locator('xpath=ancestor::*[.//button[normalize-space(.)="Confirm"] or .//*[@role="button" and normalize-space(.)="Confirm"]][1]')
        if scope.count() != 1 or not scope.is_visible() or scope.evaluate("el => ['HTML', 'BODY'].includes(el.tagName)"):
            return False
        confirm = scope.get_by_role("button", name=re.compile(r"^(Confirm|確認|確定)$")).filter(visible=True)
        if confirm.count() != 1:
            return False
        for part in category:
            option = scope.get_by_text(part, exact=True).filter(visible=True)
            try:
                option.wait_for(state="visible", timeout=3000)
            except Exception:
                pass
            if option.count() != 1 or not option.is_visible():
                cancel = scope.get_by_role("button", name=re.compile(r"^(Cancel|取消|關閉)$")).filter(visible=True)
                if cancel.count() == 1:
                    cancel.click()
                else:
                    self.page.keyboard.press("Escape")
                return False
            option.click()
        if not confirm.is_enabled():
            return False
        confirm.click()
        heading.wait_for(state="hidden", timeout=4000)
        self._locator_cache.clear()
        return self._category_matches(category)

    def _live_unverified(self, scan: dict) -> List[dict]:
        """An enabled submit button alone is never proof a live form is complete."""
        if self.mode != "shopee":
            return []
        questions = []
        for path in self._verification_paths():
            try:
                if self._path_matches(path):
                    continue
            except Exception:
                pass
            questions.append(_question("browser.manual." + hashlib.sha256(path.encode()).hexdigest()[:10], _FIELDS[path][0], "此商品欄位尚未與本輪資料核對一致。請在瀏覽器確認對應欄位後繼續。", "manual"))
        return questions

    def _images_present(self, locator, *, wait=False) -> bool:
        if locator is None:
            return False
        check = """el => {
          let group = el.closest('.image-manager, .image-uploader, [data-field-group], .shopee-form-item');
          if (!group) {
            for (let parent = el.parentElement, depth = 0; parent && depth < 7 && !['BODY','HTML'].includes(parent.tagName); parent = parent.parentElement, depth++) {
              if (parent.querySelectorAll('input[type=file]').length > 1) break;
              if (parent.querySelector('.shopee-image-manager__itembox.can-drag img.shopee-image-manager__image')) { group = parent; break; }
            }
          }
          const visible = x => x.getClientRects().length && getComputedStyle(x).visibility !== 'hidden';
          if (group && Array.from(group.querySelectorAll('[aria-busy=true], [role=progressbar], .shopee-loading-mask')).some(visible)) return false;
          return !!group && Array.from(group.querySelectorAll('.shopee-image-manager__itembox.can-drag img.shopee-image-manager__image, .image-manager__item img, .image-manager__image img, .image-uploader__preview img, [data-uploaded-image]'))
            .some(x => visible(x) && x.tagName === 'IMG' && x.complete && x.naturalWidth > 0);
        }"""
        if wait:
            try:
                self.page.wait_for_function(check, arg=locator.element_handle(), timeout=10000)
                return True
            except Exception:
                return False
        return bool(locator.evaluate(check))

    def _image_files(self, paths: Any) -> List[str]:
        if not isinstance(paths, list) or not paths or len(paths) > 9:
            raise ValueError("請提供 1 至 9 張商品圖片路徑。")
        files = []
        for raw in paths:
            if not isinstance(raw, str):
                raise ValueError("圖片路徑必須是文字。")
            candidate = (self.root / raw).resolve()
            try:
                relative = candidate.relative_to(self.root)
            except ValueError:
                raise ValueError("圖片必須位於本專案資料夾內。")
            if any(part.startswith(".") for part in relative.parts) or candidate.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                raise ValueError("僅允許專案內的 PNG、JPEG、WebP 或 GIF 商品圖片。")
            if not candidate.is_file() or candidate.stat().st_size > 10 * 1024 * 1024:
                raise ValueError("找不到圖片，或單張圖片超過 10 MB；請提供專案內有效圖片路徑。")
            with candidate.open("rb") as handle:
                header = handle.read(12)
            if not (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff") or header.startswith((b"GIF87a", b"GIF89a")) or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")):
                raise ValueError("檔案內容不是可辨識的商品圖片。")
            files.append(str(candidate))
        return files

    def _fill_control(self, path: str, value: Any, control: Optional[dict] = None) -> bool:
        if path == "product.categoryPath" and self.mode == "shopee":
            return self._choose_category(value)
        if control and control.get("type") == "radio":
            labels = [str(value)]
            if isinstance(value, bool):
                labels = ["true" if value else "false", "是" if value else "否", "有" if value else "無"]
            labels.extend({"new": ["全新"], "used": ["二手"], "wired": ["有線"], "wireless": ["無線"]}.get(str(value), []))
            groups = self._field_groups(control.get("label", ""))
            if groups.count() != 1:
                return False
            options = groups.locator('input[type="radio"]').filter(visible=True)
            matched = []
            for index in range(options.count()):
                option = options.nth(index)
                info = option.evaluate("el => ({value: el.value, label: Array.from(el.labels || []).map(x => x.innerText.trim()).join(' ')})")
                if info["value"] in labels or info["label"] in labels:
                    matched.append(option)
            if len(matched) != 1:
                return False
            matched[0].set_checked(True)
            return matched[0].is_checked()
        locator = self._locator(path, control)
        if locator is None:
            return False
        if path == "media.imagePaths":
            if self.mode == "shopee" and _get(self._listing, "media.confirmedProductImages") is not True and _get(self._listing, "media.uploadAuthorized") is not True:
                self._issues.append(_question("media.confirmedProductImages", "確認商品實拍圖片", "請確認這些圖片是本次商品可使用的圖片，才會上傳至蝦皮。", "boolean"))
                return False
            try:
                files = self._image_files(value)
            except ValueError as error:
                self._issues.append(_question(path, "商品圖片", str(error), "images"))
                return False
            if self._uploaded_paths == files:
                # A resume must not append the same images again. The current
                # gallery/upload state is checked separately before readiness.
                return self._images_present(locator) if self.mode == "shopee" else True
            if self.mode == "shopee" and self._product_id and self._images_present(locator):
                # A restarted editor cannot prove a thumbnail came from a local
                # filename. Preserve its gallery, do not append duplicates.
                self._preserved_images = True
                self._uploaded_paths = files
                return True
            if locator.get_attribute("type") == "file":
                locator.set_input_files(files)
            else:
                # Some local fixtures show paths; still validate every upload source.
                if self.mode != "demo":
                    return False
                locator.fill("\n".join(value))
            self._uploaded_paths = files
            if self.mode == "shopee":
                return self._images_present(locator, wait=True)
            return True
        kind = self._control_state(locator)
        if self.mode == "shopee" and any(_same_value(path, actual, value) for actual in kind["values"]):
            return True
        if isinstance(value, bool):
            text_value = "true" if value else "false"
        elif isinstance(value, list):
            text_value = " / ".join(str(item) for item in value)
        elif isinstance(value, (str, int, float)):
            text_value = str(value)
        else:
            return False
        if kind["type"] == "checkbox":
            if not isinstance(value, bool):
                return False
            locator.set_checked(value)
            return locator.is_checked() == value
        elif kind["tag"] == "SELECT":
            options = locator.locator("option").evaluate_all("els => els.map(e => ({value:e.value,label:e.textContent.trim()}))")
            labels = [text_value]
            if isinstance(value, bool):
                labels.extend(["是" if value else "否", "有" if value else "無"])
            labels.extend({"new": ["全新"], "used": ["二手"], "wired": ["有線"], "wireless": ["無線"]}.get(text_value, []))
            selected = next((option for option in options if option["value"] == text_value or option["label"] in labels), None)
            if not selected:
                return False
            locator.select_option(value=selected["value"])
            return locator.input_value() == selected["value"]
        elif kind["role"] == "combobox" or kind["sellerChoice"] or kind["readonly"]:
            # Hierarchical category pickers need a user; do not guess category leaves.
            if isinstance(value, list):
                return False
            locator.click()
            pattern = re.compile(r"^(?:" + "|".join(re.escape(label) for label in _value_labels(value)) + r")$", re.IGNORECASE)
            option = self.page.get_by_role("option", name=pattern).filter(visible=True)
            if kind["sellerChoice"]:
                self.page.locator(".eds-select-popover-content ul.eds-dropdown-menu").filter(visible=True).wait_for(state="visible", timeout=3000)
            if option.count() != 1:
                # Observed custom seller menus can omit role=option. Only an
                # exact, unique visible option is eligible; never create one.
                menu = self.page.locator(".eds-select-popover-content ul.eds-dropdown-menu").filter(visible=True)
                option = menu.get_by_text(pattern).filter(visible=True) if menu.count() == 1 else self.page.get_by_text(pattern).filter(visible=True)
            if option.count() != 1:
                self.page.keyboard.press("Escape")
                return False
            option.click()
            # The final form inspection verifies the selected display value once.
            return True if self.mode == "shopee" else self._control_matches(path, value, locator)
        elif kind["tag"] in ("INPUT", "TEXTAREA") or kind["editable"]:
            if kind["readonly"]:
                return False
            if kind["editable"] and self.mode == "shopee":
                # The observed Quill editor can append when filled generically.
                # Clear through keyboard input and confirm emptiness first.
                locator.click()
                locator.press("ControlOrMeta+A")
                locator.press("Backspace")
                if locator.inner_text().strip():
                    return False
                self.page.keyboard.insert_text(text_value)
            else:
                locator.fill(text_value)
            if self.mode == "shopee":
                # Do one readback in final inspection after all known fields are
                # filled, instead of reading every text value after each action.
                return True
            actual = locator.inner_text() if kind["editable"] else locator.input_value()
            return _same_value(path, actual, value)
        else:
            return False
        return True

    def fill(self, listing: dict) -> dict:
        self._check_thread()
        if self._publish_attempted:
            return self.inspect()
        if self.mode == "shopee" and self.page and not self.page.is_closed():
            try:
                current = urlparse(self.page.url)
                if self._product_id and current.hostname == "seller.shopee.tw" and current.path.startswith("/portal/product/list"):
                    self.page.goto(self._target_url, wait_until="domcontentloaded", timeout=45000)
                else:
                    self._open_new_product()
            except Exception:
                return self._result("awaiting_browser", message="新增商品頁尚未載入。請在瀏覽器確認登入與頁面後繼續。")
        gate = self._manual_gate()
        if gate:
            self._overlay(gate)
            return self._result("awaiting_browser", message=gate)
        if self.mode == "demo" and self._listing:
            current_step = self._scan().get("step")
            fields = self.page.locator("[data-field]").evaluate_all("els => els.map(el => ({path: el.dataset.field, step: el.closest('[data-step]')?.dataset.step}))")
            earlier_changed = any(field.get("step") and current_step and int(field["step"]) < int(current_step)
                                  and _get(listing, field["path"]) != _get(self._listing, field["path"])
                                  for field in fields)
            if earlier_changed:
                self._overlay("資料已更新，回到前面步驟重新填寫與核對")
                for _ in range(12):
                    back = self.page.locator('[data-action="back"]:visible')
                    if back.count() != 1:
                        break
                    back.click()
        self._listing = copy.deepcopy(listing)
        self._issues = []
        self._locator_cache.clear()
        if self.mode == "shopee":
            try:
                self._wait_for_editor()
                self._capture_existing_values()
            except Exception:
                return self._result("awaiting_browser", message="商品欄位尚未載入完成，請在目前視窗確認後繼續。")
        # Only visible steps are completed. Stop at the first missing fact.
        for _ in range(12):
            self._issues = []
            self._locator_cache.clear()
            scan = self._scan()
            signature = {(c.get("path"), c.get("label"), c.get("type"), json.dumps(c.get("options", []), sort_keys=True)) for c in scan["controls"]}
            if scan.get("step") != self._last_step:
                self._last_step = scan.get("step")
                self._overlay("正在填寫商品資料" + (" · 第 " + str(self._last_step) + " 步" if self._last_step else ""))
            attempted = set()
            controls = scan["controls"]
            if self.mode == "shopee":
                recognized = {_path_for(control) for control in controls}
                controls = controls + [{"path": path, "label": labels[0]}
                                       for path, labels in _FIELDS.items()
                                       if path not in recognized and _has_value(_get(listing, path))]
            for control in controls:
                path = _path_for(control)
                if not path or path in attempted:
                    continue
                attempted.add(path)
                value = _get(listing, path)
                if not _has_value(value):
                    continue
                try:
                    if self._fill_control(path, value, control):
                        if path not in self._filled:
                            self._filled.append(path)
                        if self.slow_mo or self.mode == "demo":
                            self._overlay("已填寫：" + control.get("label", path))
                        else:
                            self.emit("browser", "已核對：" + control.get("label", path))
                    elif control.get("required") and control.get("empty"):
                        self._issues.append(_question("browser.manual." + hashlib.sha256(path.encode()).hexdigest()[:10], control.get("label", path), "資料已提供，但此網頁控制項無法安全對應。請在瀏覽器手動填寫後繼續。", "manual"))
                except Exception:
                    self._issues.append(_question("browser.manual." + hashlib.sha256(path.encode()).hexdigest()[:10], control.get("label", path), "網頁欄位操作未完成，請在瀏覽器確認此欄位後繼續。", "manual"))
            if self.mode == "shopee":
                refreshed = self._scan()
                next_signature = {(c.get("path"), c.get("label"), c.get("type"), json.dumps(c.get("options", []), sort_keys=True)) for c in refreshed["controls"]}
                if next_signature != signature:
                    # Selecting a category can reveal more known fields. Fill
                    # those before asking the user for genuinely missing facts.
                    continue
            report = self.inspect()
            if report["phase"] in ("awaiting_info", "awaiting_browser", "published"):
                return report
            if self.mode != "demo":
                return report
            next_button = self.page.locator('[data-action="next"]:visible')
            if next_button.count() != 1:
                return report
            before = self._scan().get("step")
            next_button.click()
            try:
                self.page.wait_for_function("before => Array.from(document.querySelectorAll('[data-step]')).find(el => el.getClientRects().length)?.dataset.step !== before", arg=before, timeout=3000)
            except Exception:
                pass
            self._locator_cache.clear()
            after = self._scan().get("step")
            if before == after:
                blocked = self.inspect()
                if blocked["phase"] == "ready":
                    return self._result("awaiting_browser", message="頁面未前進到下一步，請在瀏覽器確認尚未完成的欄位後繼續。")
                return blocked
        return self._result("awaiting_browser", message="表單步驟尚未完成，請在可見視窗確認後繼續。")

    def _success_evidence(self) -> Optional[str]:
        if not self.page or self.page.is_closed():
            return None
        if self.mode == "demo":
            if self.page.locator('[data-testid="published-success"]:visible').count() == 1:
                return "本機測試頁顯示模擬上架成功；未送出蝦皮商品。"
            return None
        if self._product_id:
            # An old toast or a still-open editor cannot prove persistence.
            return self._completion_evidence if self._readback_verified else None
        parsed = urlparse(self.page.url)
        if parsed.scheme != "https" or parsed.hostname != "seller.shopee.tw":
            return None
        # A description or arbitrary page text must never masquerade as success.
        notices = self.page.locator('[role="alert"], [role="status"], .shopee-message, .shopee-notification, .shopee-toast, .shopee-modal__header').filter(visible=True)
        message = re.compile(r"^(商品新增成功|新增商品成功|商品已成功上架|已成功上架|商品上架成功)[！!。]?$")
        for index in range(notices.count()):
            content = " ".join(notices.nth(index).inner_text().split())
            if message.fullmatch(content):
                return content
        return None

    def _success_visible(self) -> bool:
        return self._success_evidence() is not None

    def _publish_button(self):
        if self.mode == "demo":
            locator = self.page.locator('[data-action="publish"]:visible')
            return locator if locator.count() == 1 else None
        if self._product_id:
            relist = self.page.get_by_role("button", name="上架", exact=True).filter(visible=True)
            unlist = self.page.get_by_role("button", name="下架", exact=True).filter(visible=True)
            # A delisted editor exposes both 上架 and 更新. Updating alone leaves
            # it delisted; prefer its explicit re-list action, bound to this ID.
            if relist.count() == 1 and unlist.count() == 0:
                self._submission_action = "relist"
                return relist
            if relist.count():
                return None
            names = ("更新",)
        else:
            names = ("儲存並上架", "儲存並刊登", "上架")
        for name in names:
            locator = self.page.get_by_role("button", name=name, exact=True).filter(visible=True)
            if locator.count() == 1 and locator.is_visible():
                self._submission_action = "update" if self._product_id else "create"
                return locator
        return None

    def _wait_for_submission_result(self) -> bool:
        try:
            # Observed seller saves disable buttons then return to the list;
            # some editor versions instead show a scoped result toast.
            self.page.wait_for_function(_SUBMISSION_SETTLED_JS,
                                        arg={"url": self._submission_url, "demo": self.mode == "demo"},
                                        timeout=15000)
            return True
        except Exception:
            return False

    def _verify_saved_update(self) -> Optional[str]:
        """Read persisted fields from a fresh editor load after the single click.

        No API endpoint is guessed. Login, incomplete load, validation errors or
        any changed field leave the attempted update unverified, without retrying.
        """
        if not (self._product_id and self._publish_attempted and self._readback_paths):
            return None
        try:
            self.page.goto(self._target_url, wait_until="domcontentloaded", timeout=45000)
            self._locator_cache.clear()
            if self._manual_gate():
                return None
            self._wait_for_editor()
            self._readback_mismatches = [path for path in self._readback_paths if not self._path_matches(path)]
            if self._submission_action == "relist":
                # List totals can be cached. Re-listing requires the freshly
                # loaded target editor to expose 下架 and no longer offer 上架.
                unlist = self.page.get_by_role("button", name="下架", exact=True).filter(visible=True)
                relist = self.page.get_by_role("button", name="上架", exact=True).filter(visible=True)
                if unlist.count() != 1 or relist.count() != 0:
                    self._readback_mismatches.append("product.publicationStatus")
            if not self._readback_mismatches and not self._scan().get("errors"):
                self._readback_verified = True
                status = "，且重新上架狀態已確認" if self._submission_action == "relist" else ""
                return "已重新載入指定商品編輯頁；%d 項欄位／圖片狀態與本輪資料核對一致%s。" % (len(self._readback_paths), status)
            return None
        except Exception:
            return None

    def inspect(self) -> dict:
        self._check_thread()
        if self._published:
            return self._result("published", message="已重新載入並核對商品更新結果。" if self._product_id else "已確認頁面顯示上架成功。")
        # A successful submit may redirect away from the creation URL.
        if self._publish_attempted and self.page and not self.page.is_closed():
            try:
                evidence = self._verify_saved_update() if self._product_id else self._success_evidence()
                if evidence:
                    self._published = True
                    self._completion_evidence = evidence
                    self._overlay("頁面已確認上架成功")
                    return self._result("published", message="已確認頁面顯示上架成功。")
            except Exception:
                pass
        gate = self._manual_gate()
        if gate:
            return self._result("awaiting_browser", message=gate)
        if self._success_visible():
            return self._result("awaiting_browser", message="頁面已有成功訊息，但本次任務尚未送出上架。請確認目前是本次商品的新增表單後繼續。")
        if self._publish_attempted:
            return self._result("awaiting_browser", message="已送出一次上架操作，尚未看到明確成功訊息。請在瀏覽器核對；系統不會重複送出。")
        scan = self._scan()
        questions = list(self._issues)
        for control in scan["controls"]:
            if not ((control.get("required") and control.get("empty")) or control.get("invalid")):
                continue
            path = _path_for(control)
            label = control.get("label", "網頁必填欄位")
            if not path:
                path = "browser.manual." + hashlib.sha256((label + str(control.get("index"))).encode()).hexdigest()[:10]
                kind = "manual"
                reason = "網頁新增了未對應的必填欄位；請在開啟的瀏覽器手動填寫，再按繼續。"
            else:
                kind = "select" if control.get("options") else "number" if control["type"] == "number" else "images" if control["type"] == "file" else "boolean" if control["type"] == "checkbox" else "text"
                reason = "目前商品頁要求此欄位，尚未取得有效值。"
                if control.get("invalid") and not control.get("empty"):
                    reason = "網頁判定此欄位格式或範圍無效，請修正資料後繼續。"
                elif _has_value(_get(self._listing, path)):
                    path = "browser.manual." + hashlib.sha256(path.encode()).hexdigest()[:10]
                    kind = "manual"
                    reason = "資料已提供，但頁面尚未接受此值。請在瀏覽器完成或核對此欄位後繼續。"
            questions.append(_question(path, label, reason, kind, control.get("options")))
        questions.extend(self._live_unverified(scan))
        unique = {}
        for question in questions:
            unique.setdefault(question["path"], question)
        questions = list(unique.values())
        errors = scan.get("errors", [])
        # Keep arbitrary page strings out of reports; expose only an error count.
        extra = {"step": scan.get("step"), "validationErrorCount": len(errors),
                 "visibleFieldCount": len(scan["controls"])}
        if questions:
            phase = "awaiting_browser" if all(q["type"] == "manual" for q in questions) else "awaiting_info"
            self._overlay("等待補充 " + str(len(questions)) + " 個欄位；瀏覽器保持開啟")
            return self._result(phase, questions, **extra)
        if errors:
            return self._result("awaiting_browser", message="商品頁仍顯示驗證訊息，請在瀏覽器檢查後繼續。", **extra)
        button = self._publish_button()
        if self.mode == "demo" and self.page.locator('[data-action="next"]:visible').count() == 1:
            return self._result("ready", message="目前步驟已完成，可繼續下一步。", **extra)
        if button is None or not button.is_enabled():
            return self._result("awaiting_browser", message="尚未找到可操作的上架按鈕。請完成商品分類、圖片或其他頁面步驟後繼續。", **extra)
        action = "重新上架" if self._submission_action == "relist" else "更新" if self._product_id else "上架"
        self._overlay("填寫完成，等待確認商品名稱後" + action)
        return self._result("ready", message="商品頁填寫完成，等待明確" + action + "確認。", **extra)

    def screenshot(self) -> bytes:
        self._check_thread()
        if not self.page or self.page.is_closed():
            return b""
        try:
            return self.page.screenshot(type="png", full_page=False, animations="disabled")
        except Exception:
            return b""

    def video_path(self) -> Optional[str]:
        """Return the recording location; close() flushes the complete video file.

        Recording is available for owned persistent contexts. CDP attachment does
        not add recording to an existing user context.
        """
        self._check_thread()
        if self._video_file:
            return self._video_file
        if self._video:
            try:
                self._video_file = str(self._video.path())
            except Exception:
                pass
        return self._video_file

    def publish(self, listing: dict, confirmation: str) -> dict:
        self._check_thread()
        title = _get(listing, "product.title")
        if not isinstance(title, str) or not title or confirmation != title:
            return self._result("awaiting_info", [_question("confirmation", "完整商品名稱", "請輸入完全相同的商品名稱，確認本次上架。")], message="未取得明確上架確認；尚未點擊上架。")
        if self._publish_attempted or self._published:
            return self.inspect()
        if json.dumps(listing, sort_keys=True, ensure_ascii=False) != json.dumps(self._listing, sort_keys=True, ensure_ascii=False):
            return self._result("awaiting_info", message="資料在預覽後已變更，請先繼續填寫並重新檢查，再確認上架。")
        report = self.inspect()
        if report["phase"] != "ready":
            return report
        button = self._publish_button()
        if button is None:
            return self._result("awaiting_browser", message="請先完成所有表單步驟，再確認上架。")
        title_input = self._locator("product.title")
        if title_input is not None:
            try:
                if title_input.input_value() != title:
                    return self._result("awaiting_info", message="瀏覽器中的商品名稱與確認名稱不同，請重新填寫並確認。")
            except Exception:
                return self._result("awaiting_browser", message="無法核對頁面商品名稱，請確認新增商品表單後繼續。")
        elif self.mode == "shopee":
            return self._result("awaiting_browser", message="無法安全核對頁面商品名稱，請在瀏覽器確認。")
        self._publish_attempted = True
        self._submission_url = self.page.url
        if self._product_id:
            self._readback_paths = self._verification_paths()
        action = "重新上架" if self._submission_action == "relist" else "更新" if self._product_id else "上架"
        self._overlay("已取得商品名稱確認，送出" + action + "一次")
        try:
            button.click(timeout=5000)
            if not self._wait_for_submission_result():
                return self._result("awaiting_browser", message="已送出一次，仍等待頁面保存結果；繼續時只讀回核對，不會再次送出。")
        except Exception:
            return self._result("awaiting_browser", message="送出結果尚未明確，請核對目前商品頁；繼續時只讀回核對，不會再次送出。")
        return self.inspect()

    def close(self):
        self._check_thread()
        try:
            if self._attached:
                if self.page and not self.page.is_closed():
                    self.page.close()
            elif self.context:
                self.context.close()
        finally:
            self.video_path()
            self.context, self.page = None, None
            self._attached = False
            self._cdp_browser = None
            if self._pw:
                self._pw.stop()
                self._pw = None
