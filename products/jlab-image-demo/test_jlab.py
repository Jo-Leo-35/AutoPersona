"""Verify confirmed model, source separation, image scope and field representations."""
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'examples/browser-demo'))
from prepare_contract import prepare_contract
from autopersona_py.schema import get_path, empty_listing, apply_answers

PRODUCT = ROOT / 'products/jlab-image-demo'
MODEL = 'JLab JBuds OPEN SPORT 開放式運動藍牙耳機'


class JlabImageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((ROOT / 'examples/browser-demo/jlab-image-input.v1.json').read_text())
        cls.prepared = prepare_contract(cls.raw, ROOT)
        cls.listing = cls.prepared['listing']

    def test_exact_model_confirmed_but_unprovided_seller_facts_stay_unknown(self):
        self.assertEqual(self.listing['product']['brand'], 'JLab')
        self.assertEqual(self.listing['product']['model'], MODEL)
        for path in ('product.condition', 'product.gtin', 'product.noValidGtin',
                     'compliance.packageContents', 'compliance.warrantyPeriod',
                     'shipping.weightKg', 'shipping.dangerousGoods', 'shipping.packageSizeCm.width',
                     'shipping.packageSizeCm.length', 'shipping.packageSizeCm.height'):
            self.assertIsNone(get_path(self.listing, path), path)
        observed = self.listing['research']['observedSiteState']
        self.assertEqual(observed['sourceType'], 'browser_observed')
        self.assertEqual(observed['observedFields']['product.condition']['value'], 'new')
        self.assertFalse(observed['observedFields']['product.condition']['applyToCanonicalListing'])

    def test_durable_user_answers_reconstruct_price_stock_model_and_main_certificate(self):
        facts = json.loads((PRODUCT / 'confirmed-facts.json').read_text())
        restored = apply_answers(empty_listing(), facts['answers'])
        for path, value in {'sales.price': 3990, 'sales.stock': 1, 'product.model': MODEL,
                            'compliance.nccNumber': 'CCAH24LPA380T2'}.items():
            self.assertEqual(get_path(restored, path), value)
            self.assertEqual(get_path(self.listing, path), value)
            self.assertEqual(facts['sources'][path]['type'], 'user_message')
        self.assertEqual(facts['sources']['sales.price']['quote'], '價格是3990')

    def test_current_certificates_match_source_and_single_field_keeps_both_ears_in_description(self):
        compliance = self.listing['compliance']
        self.assertEqual(compliance['nccNumber'], 'CCAH24LPA380T2')
        self.assertEqual(compliance['bsmiNumber'], 'R3B170')
        self.assertTrue(compliance['hasNCC'])
        self.assertTrue(compliance['hasBSMI'])
        review = self.listing['research']['certificationReview']
        self.assertEqual(review['status'], 'user_provided_matched_taiwan_distributor_product_page')
        self.assertFalse(review['blockers'])
        self.assertFalse(review['independentGovernmentDatabaseMatchCompleted'])
        self.assertEqual(review['activeNumbers']['nccRight'], 'CCAH24LPA390T5')
        self.assertTrue(review['formConstraint']['acceptsSingleCertificateOnly'])
        for value in ('左耳 CCAH24LPA380T2', '右耳 CCAH24LPA390T5'):
            self.assertIn(value, self.listing['content']['description'])
        self.assertNotIn('CCAH24LP3330T0', json.dumps(compliance))

    def test_explicit_demo_one_authorization_does_not_upload_multibrand_reference(self):
        media = self.listing['media']
        self.assertEqual(media['imagePaths'], ['demo-1.png'])
        self.assertEqual(media['referenceImagePaths'], ['demo-0.png'])
        self.assertTrue((ROOT / 'demo-1.png').is_file())
        self.assertTrue((PRODUCT / 'supplied-product.png').is_file())
        self.assertTrue(media['confirmedProductImages'])
        self.assertTrue(media['uploadAuthorized'])
        self.assertFalse(media['referenceOnly'])
        entry = next(item for item in self.prepared['fieldMap']['entries'] if item['path'] == 'media.imagePaths')
        self.assertTrue(entry['fillable'])
        self.assertFalse(self.listing['automation']['allowPublish'])

    def test_persona_restored_without_turning_internal_research_into_storefront_reviews(self):
        research = self.listing['research']
        self.assertEqual(research['matchedReviewCount'], 13)
        self.assertTrue(research['allMatchedReviewsVerifiedPurchase'])
        self.assertEqual(research['buyerSegment'], 'Missed Buyer')
        self.assertEqual(self.listing['persona']['audience'], ['需要保持環境感知的父母／照護者'])
        self.assertEqual(research['suitabilityAnalysis']['fit'], 'aligned_with_original_open_ear_positioning')
        public = json.dumps({key: self.listing[key] for key in ('product', 'persona', 'content')}, ensure_ascii=False)
        for token in ('Verified Purchase', 'Missed Buyer', '13 則', '入耳式', 'GO Air Sport',
                      'GO Sport+', 'JBuds Air Sport', 'Be Aware', '一定聽見', '安全保證', '選購參考'):
            self.assertNotIn(token, public)
        for token in ('開放式', '照護者', 'IP55', '26 小時'):
            self.assertIn(token, self.listing['content']['description'])

    def test_model_specific_specs_qualify_earbud_water_resistance_and_battery(self):
        specs = self.listing['research']['specifications']
        self.assertEqual(specs['bluetoothVersion'], '5.3')
        self.assertEqual(specs['driver']['diameterMm'], 14.2)
        self.assertEqual(specs['ipRating']['appliesTo'], 'earbuds_only')
        self.assertEqual(specs['playtimeHours']['total'], 26)
        self.assertEqual(specs['weightG'], {'singleEarbud': 9.4, 'chargingCase': 36.8})
        self.assertEqual(specs['chargeConnector'], 'Type-C')
        self.assertEqual(self.listing['compliance']['headphoneType'], '開放式')
        self.assertEqual(self.listing['compliance']['connectionType'], 'wireless')
        self.assertIn('充電盒不適用', self.listing['content']['description'])
        self.assertIn('續航依使用條件而異', self.listing['content']['description'])

    def test_old_candidates_visual_guess_and_certificate_are_explicitly_superseded(self):
        archive = json.loads((PRODUCT / 'superseded-research.json').read_text())
        self.assertEqual(archive['status'], 'superseded')
        self.assertFalse(archive['applyToStorefront'])
        self.assertEqual(archive['previousConfirmedFacts']['answers']['compliance.nccNumber'], 'CCAH24LP3330T0')
        identity = json.loads((PRODUCT / 'identity-followup.json').read_text())
        self.assertEqual(identity['currentModel'], MODEL)
        self.assertFalse(identity['previousVisualInference']['applyToStorefront'])
        self.assertEqual(identity['candidateResearchStatus'], 'stopped_and_superseded')
        self.assertNotIn('modelCandidates', self.listing['research'])

    def test_outputs_match_normalized_contract_and_all_previous_identity_blockers_are_cleared(self):
        saved = json.loads((PRODUCT / 'listing.v1.json').read_text())
        self.assertEqual(saved['listing'], self.listing)
        fields = json.loads((PRODUCT / 'field-map.v1.json').read_text())
        self.assertEqual(fields['entries'], self.prepared['fieldMap']['entries'])
        self.assertEqual(fields['blockers'], [])
        by_path = {item['path']: item for item in fields['entries']}
        for path in ('product.model', 'sales.price', 'sales.stock', 'compliance.nccNumber',
                     'compliance.bsmiNumber', 'compliance.headphoneType', 'media.imagePaths'):
            self.assertTrue(by_path[path]['fillable'], path)
        handoff = json.loads((PRODUCT / 'browser-handoff.json').read_text())
        self.assertEqual(handoff['existingProductId'], '43834400022')
        self.assertFalse(handoff['blockers'])
        self.assertEqual(handoff['certificationEarMapping'], {'left': 'CCAH24LPA380T2', 'right': 'CCAH24LPA390T5'})
        self.assertEqual(handoff['compliance']['nccNumber'], 'CCAH24LPA380T2')
        self.assertEqual(handoff['description'], self.listing['content']['description'])
        self.assertEqual(handoff['imagePaths'], ['demo-1.png'])
        self.assertEqual(handoff['referenceImagePaths'], ['demo-0.png'])


if __name__ == '__main__':
    unittest.main()
