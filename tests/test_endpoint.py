import json
from django.test import TestCase, Client
from product_filter.models import Product


class FilterEndpointTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # why: seed products into the TEMPORARY test database (auto-created/destroyed).
        #      this does NOT touch your real db.sqlite3.
        Product.objects.bulk_create([
            Product(name="single wall cup", price=120, color="white",
                    category="cups", qty_available=600, tier=1, discontinued=False),
            Product(name="double wall cup", price=80, color="kraft",
                    category="cups", qty_available=300, tier=2, discontinued=False),
            Product(name="flat lid", price=40, color="white",
                    category="lids", qty_available=900, tier=3, discontinued=True),
            Product(name="dome lid", price=200, color="black",
                    category="lids", qty_available=150, tier=1, discontinued=False),
        ])

    def setUp(self):
        self.client = Client()

    def post(self, expression):
        # helper: POST an expression as JSON, return the response
        return self.client.post(
            "/api/filter/",
            data=json.dumps({"expression": expression}),
            content_type="application/json",
        )

    # --- happy paths: 200 + correct results ---

    def test_simple_comparison_returns_results(self):
        # why: price >= 100 should return the two products over 100 (120, 200)
        resp = self.post("price >= 100")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        names = {m["name"] for m in body["results"]}
        self.assertEqual(names, {"single wall cup", "dome lid"})

    def test_and_expression(self):
        # why: cups under 100 → only double wall cup (80)
        resp = self.post('category = "cups" AND price < 100')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_or_with_parentheses(self):
        # why: the brief's grouping example — lids that are white OR black → flat lid, dome lid
        resp = self.post('category = "lids" AND (color = "white" OR color = "black")')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 2)

    def test_contains_case_insensitive(self):
        # why: CONTAINS "WALL" results "single wall cup" regardless of case (decision #3)
        resp = self.post('name CONTAINS "WALL"')
        self.assertEqual(resp.status_code, 200)
        names = {m["name"] for m in resp.json()["results"]}
        self.assertIn("single wall cup", names)

    def test_in_operator(self):
        # why: tier IN [1,2,3] → the three products with those tiers (not the tier-1 dome lid... wait, tier 1 IS in)
        resp = self.post("tier IN [1, 2, 3]")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 4)   # all four have tier in {1,2,3}

    def test_not_discontinued(self):
        # why: NOT discontinued → all except flat lid (the only discontinued one)
        resp = self.post("NOT discontinued")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 3)

    def test_between(self):
        # why: BETWEEN 50 AND 150 → double wall (80), single wall (120)
        resp = self.post("price BETWEEN 50 AND 150")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 2)

    def test_qty_available_field(self):
        # why: the brief's exact underscore field — qty_available >= 500 → single wall (600), flat lid (900)
        resp = self.post("qty_available >= 500")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 2)

    def test_empty_result(self):
        # why: a valid expression matching nothing → 200 with empty list (NOT an error)
        resp = self.post("price > 99999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)
        self.assertEqual(resp.json()["results"], [])

    # --- error paths: 400 with a message, NEVER 500 ---

    def test_unknown_field_returns_400(self):
        # why: requirement #6 — bad expression → 400, not 500
        resp = self.post('colour = "white"')      # misspelled
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_type_mismatch_returns_400(self):
        resp = self.post('price > "white"')
        self.assertEqual(resp.status_code, 400)

    def test_malformed_syntax_returns_400(self):
        resp = self.post("price > > 100")
        self.assertEqual(resp.status_code, 400)

    def test_illegal_character_returns_400(self):
        resp = self.post("price > @")
        self.assertEqual(resp.status_code, 400)

    # --- request-level errors ---

    def test_missing_expression_key_returns_400(self):
        # why: request envelope is wrong (no 'expression' key) → 400
        resp = self.client.post(
            "/api/filter/",
            data=json.dumps({"wrong_key": "price > 100"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_post_returns_405(self):
        # why: GET is not allowed on this endpoint
        resp = self.client.get("/api/filter/")
        self.assertEqual(resp.status_code, 405)