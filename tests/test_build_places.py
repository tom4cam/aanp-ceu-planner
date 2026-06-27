import os, sys, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import build_places as B

class TestMerge(unittest.TestCase):
    def test_curated_wins_on_name_collision(self):
        raw = [{'id':'r1','name':'Grand Lux Cafe','cat':'sitdown','area':'Grand Canal Shoppes','placed':False}]
        cur = [{'id':'c1','name':'grand lux cafe','cat':'sitdown','area':'Grand Canal Shoppes','placed':True,'map':'gcs','x':0.3,'y':0.4}]
        out = B.merge(raw, cur)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]['placed'])
        self.assertEqual(out[0]['id'], 'c1')

    def test_keeps_distinct_rows(self):
        raw = [{'id':'r1','name':'Tory Burch','cat':'shop','area':'Grand Canal Shoppes','placed':False}]
        cur = [{'id':'c1','name':'Starbucks','cat':'coffee','area':'Expo','placed':True,'map':'expo2','x':0.5,'y':0.5}]
        out = B.merge(raw, cur)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['id'], 'c1')  # curated first

    def test_to_js_emits_global_and_valid_json(self):
        js = B.to_js([{'id':'c1','name':'X','cat':'coffee','area':'Expo','placed':True}])
        self.assertTrue(js.startswith('window.PLACES = '))
        self.assertTrue(js.rstrip().endswith(';'))
        payload = js[len('window.PLACES = '):].rstrip().rstrip(';')
        json.loads(payload)  # must be valid JSON

if __name__ == '__main__':
    unittest.main()
