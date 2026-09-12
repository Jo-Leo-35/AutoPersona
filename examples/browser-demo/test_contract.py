"""Boundaries for the swappable Persona contract; no API or browser required."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from prepare_contract import VERSION, prepare_contract
from autopersona_py.planner import normalize_listing
from autopersona_py.schema import FIELDS, get_path


class BrowserDemoContractTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((HERE / 'persona-input.v1.json').read_text())

    def test_preparation_never_reads_config_or_calls_model(self):
        with patch('autopersona_py.planner._read_config', side_effect=AssertionError('config read')), \
                patch('autopersona_py.planner._generate_ai_copy', side_effect=AssertionError('API call')):
            prepared = prepare_contract(self.raw)
        self.assertFalse(prepared['processing']['apiCalled'])
        self.assertFalse(prepared['processing']['configRead'])
        self.assertFalse(prepared['processing']['browserOperated'])

    def test_only_title_and_description_are_actionable_in_this_demo(self):
        prepared = prepare_contract(self.raw)
        entries = prepared['fieldMap']['entries']
        self.assertEqual({entry['path'] for entry in entries if entry['fillable']},
                         {'product.title', 'content.description'})
        self.assertEqual({entry['path'] for entry in entries}, set(FIELDS))
        self.assertFalse(prepared['fieldMap']['allowPublish'])
        self.assertEqual(prepared['listing']['automation'], {'mode': 'draft_only', 'allowPublish': False})

    def test_unknown_sellable_facts_are_not_inferred_from_persona_or_reference_images(self):
        prepared = prepare_contract(self.raw)
        paths = ['product.brand', 'product.model', 'product.condition', 'product.gtin',
                 'product.noValidGtin', 'sales.price', 'sales.stock', 'sales.minPurchaseQty',
                 'shipping.weightKg', 'shipping.dangerousGoods',
                 'shipping.packageSizeCm.width', 'shipping.packageSizeCm.length',
                 'shipping.packageSizeCm.height', 'compliance.connectionType',
                 'compliance.hasNCC', 'compliance.hasBSMI', 'compliance.nccNumber',
                 'compliance.bsmiNumber', 'compliance.packageContents',
                 'compliance.warrantyPeriod', 'compliance.warrantyType']
        for path in paths:
            self.assertIsNone(get_path(prepared['listing'], path), path)

    def test_research_stays_internal_and_reference_images_are_not_authorized(self):
        prepared = prepare_contract(self.raw)
        listing = prepared['listing']
        self.assertEqual(listing['research']['matchedReviewCount'], 13)
        self.assertTrue(listing['research']['allMatchedReviewsVerifiedPurchase'])
        self.assertEqual(listing['research']['buyerSegment'], 'Missed Buyer')
        public = json.dumps({key: listing[key] for key in ('product', 'persona', 'content')}, ensure_ascii=False)
        handoff = json.dumps(prepared['fieldMap'], ensure_ascii=False)
        for token in ('Verified Purchase', 'Missed Buyer', '13 則'):
            self.assertNotIn(token, public)
            self.assertNotIn(token, handoff)
        self.assertEqual(listing['media']['imagePaths'], [])
        self.assertEqual(listing['media']['referenceImagePaths'], ['demo-0.png', 'demo-1.png'])
        self.assertFalse(listing['media']['uploadAuthorized'])
        self.assertFalse(listing['media']['confirmedProductImages'])

    def test_source_is_unchanged_and_normalization_is_idempotent(self):
        snapshot = deepcopy(self.raw)
        result = prepare_contract(self.raw)
        self.assertEqual(self.raw, snapshot)
        self.assertEqual(normalize_listing(result['listing']), result['listing'])

    def test_version_or_envelope_errors_are_rejected(self):
        variants = [None, {}, {**self.raw, 'schemaVersion': '2.0.0'},
                    {**self.raw, 'listing': []}, {**self.raw, 'exampleId': ''},
                    {**self.raw, 'sales': {'price': 10}}]
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                prepare_contract(raw)

    def test_exact_aliases_zero_and_false_follow_existing_normalizer(self):
        raw = deepcopy(self.raw)
        raw['listing']['sales']['stock'] = '0'
        raw['listing']['shipping'].pop('dangerousGoods')
        raw['listing']['shipping']['dangerous_goods'] = 'false'
        result = prepare_contract(raw)
        self.assertEqual(result['listing']['sales']['stock'], 0)
        self.assertIs(result['listing']['shipping']['dangerousGoods'], False)
        entries = {item['path']: item for item in result['fieldMap']['entries']}
        self.assertTrue(entries['sales.stock']['fillable'])
        self.assertTrue(entries['shipping.dangerousGoods']['fillable'])

    def test_conflicting_confirmation_is_rejected_by_existing_normalizer(self):
        raw = deepcopy(self.raw)
        raw['listing']['product'].update({'gtin': 'confirmed-barcode', 'noValidGtin': True})
        with self.assertRaises(ValueError):
            prepare_contract(raw)

    def test_legacy_true_alone_cannot_mark_reference_images_fillable(self):
        raw = deepcopy(self.raw)
        raw['listing']['media'].update({'imagePaths': ['demo-1.png'], 'uploadAuthorized': True})
        result = prepare_contract(raw)
        image = next(entry for entry in result['fieldMap']['entries'] if entry['path'] == 'media.imagePaths')
        self.assertFalse(image['fillable'])
        self.assertEqual(image['status'], 'withheld')

    def test_confirmed_and_authorized_product_file_can_be_proposed_for_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'actual-product.png').write_bytes(b'test file for path check only')
            raw = deepcopy(self.raw)
            raw['listing']['media'].update({'imagePaths': ['actual-product.png'],
                                          'uploadAuthorized': True,
                                          'confirmedProductImages': True,
                                          'referenceOnly': False})
            result = prepare_contract(raw, root)
        image = next(entry for entry in result['fieldMap']['entries'] if entry['path'] == 'media.imagePaths')
        self.assertTrue(image['fillable'])
        self.assertFalse(result['fieldMap']['allowPublish'])

    def test_generated_files_match_the_current_source(self):
        result = prepare_contract(self.raw)
        expected = {
            'normalized.v1.json': {key: result[key] for key in ('schemaVersion', 'exampleId', 'listing')},
            'field-map.v1.json': result['fieldMap'],
            'questions.v1.json': {'schemaVersion': VERSION, 'questions': result['questions']},
        }
        for name, value in expected.items():
            self.assertEqual(json.loads((HERE / name).read_text()), value, name)

    def test_template_has_no_product_or_copy_assumptions(self):
        raw = json.loads((HERE / 'persona-input.template.v1.json').read_text())
        result = prepare_contract(raw)
        for path in FIELDS:
            self.assertIn(get_path(result['listing'], path), (None, []), path)
        self.assertFalse(any(entry['fillable'] for entry in result['fieldMap']['entries']))

    def test_canonical_json_schema_covers_every_python_field(self):
        schema = json.loads((HERE / 'persona-input.schema.v1.json').read_text())
        self.assertEqual(schema['properties']['schemaVersion']['const'], VERSION)
        for path, (kind, _label, _required, options) in FIELDS.items():
            node = schema['properties']['listing']
            for part in path.split('.'):
                self.assertIn(part, node['required'], path)
                node = node['properties'][part]
            if kind == 'select':
                self.assertEqual(node['enum'], [None] + options)
            elif kind == 'array':
                self.assertEqual(node['type'], 'array')
            else:
                scalar = {'text': 'string', 'number': 'number', 'integer': 'integer', 'boolean': 'boolean'}[kind]
                self.assertEqual(node['type'], [scalar, 'null'])


if __name__ == '__main__':
    unittest.main()
