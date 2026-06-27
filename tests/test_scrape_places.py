import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import scrape_places as S

FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'gcs_sample.html')

class TestParse(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding='utf-8') as f:
            self.html = f.read()

    def test_parses_each_card(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        names = sorted(r['name'] for r in rows)
        self.assertEqual(names, ['Bouchon Bakery', 'Grand Lux Cafe', 'Tory Burch'])

    def test_sets_area_and_unplaced(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        self.assertTrue(all(r['area'] == 'Grand Canal Shoppes' for r in rows))
        self.assertTrue(all(r['placed'] is False for r in rows))

    def test_categorize_maps_to_known_buckets(self):
        self.assertEqual(S.categorize('Grand Lux Cafe', 'Restaurant'), 'sitdown')
        self.assertEqual(S.categorize('Bouchon Bakery', 'Cafe'), 'coffee')
        self.assertEqual(S.categorize('Tory Burch', "Women's Apparel"), 'shop')

    def test_ids_are_unique_slugs(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        ids = [r['id'] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))

if __name__ == '__main__':
    unittest.main()
