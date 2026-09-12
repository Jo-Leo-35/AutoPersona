#!/usr/bin/env python3
"""Rebuild the user-confirmed JBuds OPEN SPORT draft with canonical normalization."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'examples/browser-demo'))
from prepare_contract import prepare_contract
from autopersona_py.schema import empty_listing, apply_answers

PRODUCT = ROOT / 'products/jlab-image-demo'
SOURCE_URL = 'https://store.igogosport.com/products/jlab-jbuds-open-sport'
TITLE = 'JLab JBuds OPEN SPORT 開放式運動藍牙耳機 黑色｜耳掛設計'
DESCRIPTION = '''JLab JBuds OPEN SPORT 開放式運動藍牙耳機，採不入耳設計與可調整耳掛。給希望在聆聽音樂或節目時，仍保留與家人及周遭互動的父母與照護者，多一種日常聆聽選擇。實際環境聲感受會隨播放音量與周遭噪音改變，使用時仍需留意照護情況。

商品特色
・開放式設計，不將耳塞深入耳道
・可調整耳掛，依耳形調整佩戴
・藍牙 5.3，搭載 14.2 mm 動圈單體
・耳機具 IP55 防塵防水等級；充電盒不適用
・單耳播放 9 小時以上，充電盒另供 17 小時，總計約 26 小時；續航依使用條件而異
・Type-C 充電，約 2 小時充電時間

商品規格
型號：JLab JBuds OPEN SPORT
音頻解碼：SBC、AAC
支援協議：HSP／HFP／A2DP／AVRCP
麥克風：MEMS，-38 dB ±1 dB
頻率響應：20 Hz–20 kHz
重量：單耳 9.4 g；充電盒 36.8 g
充電盒電池容量：500 mAh
NCC：左耳 CCAH24LPA380T2；右耳 CCAH24LPA390T5
BSMI：R3B170'''


def read(name):
    return json.loads((PRODUCT / name).read_text(encoding='utf-8'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def build():
    original = json.loads((ROOT / 'examples/browser-demo/persona-input.v1.json').read_text())['listing']
    confirmed, model_facts = read('confirmed-facts.json'), read('product-facts.json')
    observed, review = read('observed-site-state.json'), read('certification-review.json')
    listing = empty_listing()
    listing['product'].update({'title': TITLE, 'categoryPath': ['影音', '耳機/耳麥/藍牙耳機']})
    listing['persona'] = deepcopy(original['persona'])
    listing['persona']['positioning'] = '給希望聆聽時保留與家人及周遭互動的父母／照護者，提供開放式日常聆聽選擇。'
    listing['content'] = {
        'description': DESCRIPTION,
        'highlights': ['開放式不入耳設計與可調整耳掛', '藍牙 5.3 與 14.2 mm 動圈單體',
                       '耳機 IP55 防塵防水，充電盒不適用', '單耳 9 小時以上，含充電盒總計約 26 小時'],
        'keywords': ['JLab', 'JBuds OPEN SPORT', '開放式耳機', '耳掛式耳機', '藍牙耳機'],
    }
    listing['media'].update({
        'imagePaths': ['demo-1.png'],
        'referenceImagePaths': ['demo-0.png'], 'referenceOnly': False,
        'confirmedProductImages': True, 'uploadAuthorized': True,
    })
    # Durable seller/model answers and observed site labels remain separate sources.
    listing = apply_answers(listing, confirmed['answers'])
    site_answers = {path: item['value'] for path, item in observed['fieldMappings'].items()
                    if item['applyToCanonicalListing']}
    listing = apply_answers(listing, site_answers)
    listing['research'] = {
        'internalOnly': True, 'personaBrief': original['personaBrief'],
        'matchedReviewCount': 13, 'allMatchedReviewsVerifiedPurchase': True,
        'buyerSegment': 'Missed Buyer',
        'reviewUseNote': '這 13 則是使用者提供的 Persona 研究命中，不是本次商品評論、驗證購買見證或安全證據。',
        'originalPersona': deepcopy(original['persona']),
        'sourceStatement': '使用者明確提供正式型號與規格；台灣代理該型號商品頁的型號、規格及左右耳字號已核對吻合。',
        'imageAuthorization': {'confirmedByUser': True, 'uploadAuthorizedByUser': True,
                               'scope': '使用者要求導入兩圖；主 agent 依圖片內容配置 demo-1.png 為商品圖、demo-0.png 為內部多品牌參考，角色配置不是使用者逐圖原話。'},
        'imageEvidence': {
            'path': 'demo-1.png',
            'sha256': hashlib.sha256((ROOT / 'demo-1.png').read_bytes()).hexdigest(),
            'originalSourceCopy': 'products/jlab-image-demo/supplied-product.png',
            'originalSourceSha256': hashlib.sha256((PRODUCT / 'supplied-product.png').read_bytes()).hexdigest(),
            'referenceOnlyImage': 'demo-0.png',
            'observed': ['JLab 圓形品牌標誌', '黑色耳掛', '左右分離耳機與充電盒'],
            'identitySource': 'explicit_user_model_and_taiwan_distributor_product_page',
            'visualInferenceCorrection': '先前將突出單體判為入耳式屬錯誤推論，已由正式型號來源更正為開放式。',
        },
        'identityAssessment': {
            'brand': 'JLab', 'model': listing['product']['model'],
            'modelStatus': 'user_confirmed_and_distributor_source_matched',
            'productType': '開放式，不入耳',
            'conclusion': '正式型號與來源優先於舊視覺猜測；候選研究已停止，舊入耳式分類不再適用。',
        },
        'specifications': deepcopy(model_facts['specifications']),
        'modelFactSource': deepcopy(model_facts['source']),
        'confirmedFactSources': deepcopy(confirmed['sources']),
        'observedSiteState': deepcopy(observed), 'certificationReview': deepcopy(review),
        'suitabilityAnalysis': {
            'originalAudience': '需要保持環境感知的父母／照護者',
            'originalNeed': '照護時希望留意周遭動靜',
            'assessedProductType': '開放式，不入耳，帶可調整耳掛',
            'fit': 'aligned_with_original_open_ear_positioning',
            'basis': '正式型號產品頁確認開放式設計；因此恢復原 Persona 聆聽時保留周遭互動的情境。',
            'evidenceLimit': '受眾需求與設計相符是文案定位判斷，不代表經測試可辨識每種哭聲、警報或照護事件。',
            'ambientModeStatus': 'open_ear_design_confirmed_no_electronic_ambient_mode_claim',
            'doNotClaim': ['一定聽見哭聲或警報', '照護／交通安全保證', '已驗證的本商品買家好評',
                           '主動降噪或 Be Aware 模式', '充電盒具 IP55 防水', '每次都能播放 26 小時'],
            'copyDecision': '以開放式結構、可調耳掛與核實規格寫商品文案，提及照護者日常聆聽需求但不作安全保證。',
        },
        'supersededResearch': {'status': 'superseded', 'applyToStorefront': False,
                               'file': 'products/jlab-image-demo/superseded-research.json',
                               'reason': '使用者提供正式型號與該型號來源；舊圖片候選、入耳式推論及舊 NCC 值失效。'},
        'sources': [{'id': 'jbuds_open_sport_tw', 'type': 'taiwan_distributor_product_page',
                     'url': SOURCE_URL, 'accessedOn': '2026-09-12',
                     'purpose': '核對型號、開放式設計、商品規格與左右耳 NCC／BSMI；不套用零售商價格庫存與保固資格。'}],
    }
    raw = {'schemaVersion': '1.0.0', 'exampleId': 'jlab-user-supplied-image-2026-09-12', 'listing': listing}
    prepared = prepare_contract(raw, ROOT)
    blockers = deepcopy(review['blockers'])
    prepared['fieldMap']['blockers'] = blockers
    save(ROOT / 'examples/browser-demo/jlab-image-input.v1.json', raw)
    save(PRODUCT / 'listing.v1.json', {key: prepared[key] for key in ('schemaVersion', 'exampleId', 'listing')})
    save(PRODUCT / 'field-map.v1.json', prepared['fieldMap'])
    save(PRODUCT / 'questions.v1.json', {
        'schemaVersion': '1.0.0', 'questions': prepared['questions'], 'blockers': blockers,
        'alreadyObservedOnExistingPage': observed['observedFields'],
        'instruction': '僅依實站需要集中提問；商品狀況全新已在既有頁觀測，沿用頁面值，不因本列表再次提問。',
    })
    save(PRODUCT / 'research.json', listing['research'])
    save(PRODUCT / 'browser-handoff.json', {
        'existingProductId': observed['existingProductId'],
        'title': TITLE, 'description': DESCRIPTION, 'model': listing['product']['model'],
        'blockers': blockers, 'certificationStatus': review['status'],
        'certificationEarMapping': model_facts['certifications']['ncc'],
        'nccFormConstraint': review['formConstraint'],
        'imagePaths': listing['media']['imagePaths'],
        'referenceImagePaths': listing['media']['referenceImagePaths'],
        'imageRoles': {'demo-1.png': 'user_confirmed_product_image',
                       'demo-0.png': 'internal_multibrand_reference_do_not_upload'},
        'sales': deepcopy(listing['sales']),
        'compliance': deepcopy(listing['compliance']),
        'specifications': deepcopy(model_facts['specifications']), 'allowPublish': False,
        'pageAttributeSuggestions': [
            {'label': '品牌', 'value': 'JLab', 'basis': '使用者正式型號與代理來源'},
            {'label': '耳機類型', 'value': listing['compliance']['headphoneType'],
             'basis': observed['fieldMappings']['compliance.headphoneType']['basis']},
            {'label': '連接類型', 'value': '無線', 'basis': '藍牙 5.3 規格'},
        ],
        'retainExistingPageValues': observed['observedFields'],
        'leaveBlank': ['完整包裝清單', '保固', '物流重量與尺寸'], 'source': SOURCE_URL,
    })
    print(json.dumps({'product': listing['product'], 'sales': listing['sales'],
                      'certificationStatus': review['status'], 'blockerCount': len(blockers),
                      'questionCount': len(prepared['questions'])}, ensure_ascii=False))


if __name__ == '__main__':
    build()
