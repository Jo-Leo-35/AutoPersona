"""Observed editor markup exercised locally; no real Shopee requests are made."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autopersona_py.browser import BrowserSession, _same_value
from test_browser import PNG


EDITOR = r'''<!doctype html><html><head><meta charset="utf-8"></head><body>
<span>商品名稱</span><input id="title" placeholder="品牌名稱 + 商品類型 + 重要功能">
<div>影音 &gt; 耳機/耳麥/藍牙耳機</div>
<div class="product-brand-item"><span>品牌</span><div id="brand" class="eds-selector" onclick="choose(this,['TESTLAB','OTHER'])"><span class="eds-selector__inner"></span></div></div>
<div class="product-attribute-item-100519"><span>* 耳機類型</span><div id="headphone" class="eds-selector" onclick="choose(this,['入耳式 (含耳道式)','開放式'])"><span class="eds-selector__inner"></span></div></div>
<div class="product-attribute-item-100408"><span>* 連接類型</span><div id="connection" class="eds-selector" onclick="choose(this,['有線','無線'])"><span class="eds-selector__inner"></span></div></div>
<div class="product-attribute-item-100970"><span>* NCC</span><input id="ncc" required></div>
<div class="product-attribute-item-100969"><span>* BSMI</span><input id="bsmi" required></div>
<div class="basic-price"><span>* 價格</span><input id="price" required></div>
<div class="basic-stock"><span>* 商品數量</span><input id="stock" required></div>
<div><span>商品描述</span><div id="description" class="ql-editor" contenteditable="true"></div><div class="ql-clipboard" contenteditable="true" hidden></div></div>
<section><input id="productImages" type="file" accept="image/*" multiple hidden><div class="shopee-image-manager__itembox can-drag"><img class="shopee-image-manager__image" width="32" height="32" src="__IMAGE__"></div></section>
<section><input id="marketingImage" type="file" accept="image/*" hidden><img width="32" height="32" src="__IMAGE__"></section>
<div class="eds-select-popover-content" hidden><ul class="eds-dropdown-menu"></ul></div>
<button id="update" onclick="save()">更新</button>
__ACTIONS__
<script>
const state=__STATE__;
for(const id of ['title','ncc','bsmi','price','stock'])document.getElementById(id).value=state[id];
for(const id of ['brand','headphone','connection'])document.getElementById(id).querySelector('.eds-selector__inner').textContent=state[id];
document.getElementById('description').innerText=state.description;
function choose(field, options){const popover=document.querySelector('.eds-select-popover-content');const menu=popover.querySelector('ul');menu.replaceChildren();for(const value of options){const option=document.createElement('li');option.setAttribute('role','option');option.textContent=value;option.onclick=()=>{field.querySelector('.eds-selector__inner').textContent=value;popover.hidden=true};menu.append(option)}popover.hidden=false}
async function save(action='update'){const data={action};for(const id of ['title','ncc','bsmi','price','stock'])data[id]=document.getElementById(id).value;for(const id of ['brand','headphone','connection'])data[id]=document.getElementById(id).querySelector('.eds-selector__inner').textContent;data.description=document.getElementById('description').innerText;await fetch('/fixture-save',{method:'POST',body:JSON.stringify(data)});const notice=document.createElement('div');notice.setAttribute('role','status');notice.textContent='更新成功';document.body.append(notice)}
</script></body></html>'''


class ShopeeAdapterBoundaryTests(unittest.TestCase):
    def test_target_id_is_validated_before_launch(self):
        for product_id in ("../new", "42?token=value", 42, "", "１２"):
            with self.subTest(product_id=product_id), self.assertRaises(ValueError):
                BrowserSession(Path.cwd()).start({}, "shopee", "", product_id=product_id)

    def test_cdp_environment_never_silently_attaches_user_browser(self):
        with patch.dict(os.environ, {"AUTOPERSONA_CDP_URL": "http://127.0.0.1:9999"}):
            self.assertIsNone(BrowserSession(Path.cwd()).cdp_url)

    def test_certification_and_zero_stock_comparison_are_exact(self):
        self.assertTrue(_same_value("sales.stock", "0", 0))
        self.assertFalse(_same_value("sales.stock", "1", 0))
        self.assertFalse(_same_value("compliance.nccNumber", "CCAH24LPA380T2CCAH24LPA390T5", "CCAH24LPA380T2"))
        self.assertFalse(_same_value("compliance.nccNumber", "CCAH24LPA380T3", "CCAH24LPA380T2"))


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Install Python Playwright for local editor tests")
class ShopeeObservedEditorTests(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        import base64
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "item.png").write_bytes(PNG)
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.persisted = {"title": "舊商品", "description": "旧內容不可殘留", "brand": "OTHER",
                          "headphone": "入耳式 (含耳道式)", "connection": "有線", "ncc": "OLDNCC",
                          "bsmi": "OLDBSMI", "price": "20", "stock": "0"}
        self.accept_save = True
        self.accept_relist = True
        self.live = True
        self.submissions = 0
        self.actions = []
        image = "data:image/png;base64," + base64.b64encode(PNG).decode()

        def intercept(route):
            if route.request.url.endswith("/fixture-save"):
                self.submissions += 1
                submitted = json.loads(route.request.post_data)
                action = submitted.pop('action')
                self.actions.append(action)
                if self.accept_save:
                    self.persisted = submitted
                    if action == 'relist' and self.accept_relist:
                        self.live = True
                route.fulfill(status=200, content_type="application/json", body="{}")
            else:
                actions = '<button id="unlist">下架</button>' if self.live else '<button id="relist" onclick="save(\'relist\')">上架</button>'
                route.fulfill(status=200, content_type="text/html", body=EDITOR.replace("__STATE__", json.dumps(self.persisted)).replace("__IMAGE__", image).replace("__ACTIONS__", actions))

        # Every request, including the seller-looking URL, is intercepted locally.
        self.context.route("**/*", intercept)
        self.page.goto("https://seller.shopee.tw/portal/product/123")
        self.session = BrowserSession(self.root, headless=True, slow_mo=0)
        self.session.page = self.page
        self.session.context = self.context
        self.session.mode = "shopee"
        self.session._product_id = "123"
        self.session._target_url = self.page.url
        self.listing = {"product": {"title": "測試開放式商品", "categoryPath": ["影音", "耳機/耳麥/藍牙耳機"], "brand": "TESTLAB"},
                        "content": {"description": "替換後的第一段\n第二段：只使用提供的商品事實。"},
                        "compliance": {"headphoneType": "開放式", "connectionType": "wireless", "nccNumber": "TEST1234", "bsmiNumber": "RTEST1"},
                        "sales": {"price": 3990, "stock": 1},
                        "media": {"imagePaths": ["item.png"], "uploadAuthorized": True}}

    def tearDown(self):
        self.browser.close()
        self.pw.stop()
        self.temp.cleanup()

    def test_existing_update_replaces_quill_and_verifies_persisted_fields(self):
        with patch.object(self.page, 'wait_for_timeout', side_effect=AssertionError('fixed delay')):
            result = self.session.fill(self.listing)
        self.assertEqual(result["phase"], "ready", result)
        self.assertEqual(self.page.locator(".ql-editor").inner_text(), self.listing["content"]["description"])
        self.assertEqual(self.page.locator("#headphone .eds-selector__inner").inner_text(), "開放式")
        self.assertTrue(result["browser"]["existingImagesPreserved"])
        self.assertEqual(self.page.locator("#productImages").evaluate("el => el.files.length"), 0)
        self.assertFalse(result["browser"]["completionVerified"])
        with patch.object(self.page, 'wait_for_timeout', side_effect=AssertionError('fixed delay')):
            result = self.session.publish(self.listing, self.listing["product"]["title"])
        self.assertEqual(result["phase"], "published", result)
        self.assertTrue(result["browser"]["readbackVerified"])
        self.assertEqual(result["browser"]["operation"], "update")
        self.assertEqual(self.persisted["stock"], "1")
        self.assertEqual(self.persisted["ncc"], "TEST1234")
        self.session.publish(self.listing, self.listing["product"]["title"])
        self.assertEqual(self.submissions, 1)

    def test_same_editor_url_without_persistence_never_counts_as_success(self):
        self.accept_save = False
        self.assertEqual(self.session.fill(self.listing)["phase"], "ready")
        result = self.session.publish(self.listing, self.listing["product"]["title"])
        self.assertEqual(result["phase"], "awaiting_browser", result)
        self.assertTrue(result["publishAttempted"])
        self.assertFalse(result["browser"]["completionVerified"])
        self.assertIn("content.description", result["browser"]["readbackMismatchPaths"])
        self.session.publish(self.listing, self.listing["product"]["title"])
        self.assertEqual(self.submissions, 1)

    def test_null_sales_and_empty_media_keep_existing_values_then_verify_them(self):
        listing = copy.deepcopy(self.listing)
        listing['sales'] = {'price': None, 'stock': None}
        listing['media'] = {'imagePaths': [], 'uploadAuthorized': False, 'confirmedProductImages': False}
        result = self.session.fill(listing)
        self.assertEqual(result['phase'], 'ready', result)
        self.assertEqual(self.page.locator('#price').input_value(), '20')
        self.assertEqual(self.page.locator('#stock').input_value(), '0')
        self.assertTrue(result['browser']['existingImagesPreserved'])
        result = self.session.publish(listing, listing['product']['title'])
        self.assertEqual(result['phase'], 'published', result)
        self.assertEqual(result['browser']['retainedExistingFields'], ['sales.price', 'sales.stock'])
        self.assertEqual(self.persisted['price'], '20')
        self.assertEqual(self.persisted['stock'], '0')
        self.assertIsNone(listing['sales']['price'])
        self.assertEqual(self.submissions, 1)

    def test_delisted_editor_relists_once_and_verifies_fresh_live_status(self):
        self.live = False
        self.page.reload()
        result = self.session.fill(self.listing)
        self.assertEqual(result['phase'], 'ready', result)
        self.assertEqual(result['browser']['operation'], 'relist')
        self.assertEqual(self.page.get_by_role('button', name='更新', exact=True).count(), 1)
        result = self.session.publish(self.listing, self.listing['product']['title'])
        self.assertEqual(result['phase'], 'published', result)
        self.assertEqual(result['browser']['operation'], 'relist')
        self.assertTrue(result['browser']['readbackVerified'])
        self.assertEqual(self.page.get_by_role('button', name='下架', exact=True).count(), 1)
        self.assertEqual(self.actions, ['relist'])
        self.session.publish(self.listing, self.listing['product']['title'])
        self.assertEqual(self.submissions, 1)

    def test_saved_fields_without_live_status_cannot_confirm_relisting(self):
        self.live = False
        self.accept_relist = False
        self.page.reload()
        self.assertEqual(self.session.fill(self.listing)['phase'], 'ready')
        result = self.session.publish(self.listing, self.listing['product']['title'])
        self.assertEqual(result['phase'], 'awaiting_browser', result)
        self.assertFalse(result['browser']['completionVerified'])
        self.assertEqual(result['browser']['readbackMismatchPaths'], ['product.publicationStatus'])
        self.assertEqual(self.persisted['title'], self.listing['product']['title'])
        # A later explicit inspect may confirm the earlier operation, never click again.
        self.live = True
        result = self.session.inspect()
        self.assertEqual(result['phase'], 'published', result)
        self.assertEqual(self.actions, ['relist'])

    def test_missing_choice_and_wrong_product_never_change_another_product(self):
        listing = copy.deepcopy(self.listing)
        listing["compliance"]["headphoneType"] = "未提供的選項"
        self.assertEqual(self.session.fill(listing)["phase"], "awaiting_browser")
        self.assertEqual(self.page.locator("#headphone .eds-selector__inner").inner_text(), "入耳式 (含耳道式)")
        self.page.goto("https://seller.shopee.tw/portal/product/456")
        self.assertEqual(self.session.fill(self.listing)["phase"], "awaiting_browser")
        self.assertEqual(self.page.locator("#title").input_value(), "舊商品")
        self.assertEqual(self.submissions, 0)


if __name__ == "__main__":
    unittest.main()
