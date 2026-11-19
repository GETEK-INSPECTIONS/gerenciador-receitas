"""HTTP integration checks against an isolated temporary recipe notebook."""

import json
import base64
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PIL import Image

from recipes.web import create_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.server = create_server(Path(self.directory.name) / "recipes.db", port=0)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.recipe = {"title": "Pancakes", "category": "Breakfast", "servings": 2,
                       "ingredients": [{"name": "Flour", "quantity": 500, "unit": "g"}],
                       "steps": ["Mix.", "Cook."]}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, path, method="GET", data=None, headers=None):
        body = json.dumps(data).encode() if data is not None else None
        defaults = {"Content-Type": "application/json", "X-Recipe-Manager": "1"}
        defaults.update(headers or {})
        request = Request(self.base + path, data=body, method=method, headers=defaults)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            if "application/json" in response.headers.get("Content-Type", ""):
                payload = json.loads(payload)
            return response.status, payload

    def create_recipe(self, recipe=None):
        status, result = self.request("/api/recipes", "POST", recipe or self.recipe)
        self.assertEqual(status, 201, result)
        return result["id"]

    def test_recipe_crud_validation_and_filtering(self):
        recipe_id = self.create_recipe()
        status, items = self.request("/api/recipes?name=PAN&category=breakfast")
        self.assertEqual(status, 200)
        self.assertEqual(items[0]["id"], recipe_id)
        invalid = {**self.recipe, "servings": 0}
        self.assertEqual(self.request(f"/api/recipes/{recipe_id}", "PUT", invalid)[0], 400)
        self.assertEqual(self.request("/api/recipes")[1][0]["servings"], 2)
        edited = {**self.recipe, "title": "Weekend pancakes"}
        self.assertEqual(self.request(f"/api/recipes/{recipe_id}", "PUT", edited)[0], 200)
        self.assertEqual(self.request("/api/recipes")[1][0]["title"], edited["title"])
        self.assertEqual(self.request(f"/api/recipes/{recipe_id}", "DELETE")[0], 200)
        self.assertEqual(self.request("/api/recipes")[1], [])

    def test_plan_persists_and_protects_recipes(self):
        recipe_id = self.create_recipe()
        status, entry = self.request("/api/meals", "POST", {
            "day": "2026-11-19", "meal": "Lunch", "recipe_id": recipe_id, "servings": 4})
        self.assertEqual(status, 201)
        plan = self.request("/api/meals?week=2026-11-20")[1]
        self.assertEqual(plan["week"], "2026-11-16")
        self.assertEqual(plan["entries"][0]["recipe_id"], recipe_id)
        self.assertEqual(self.request(f"/api/recipes/{recipe_id}", "DELETE")[0], 400)
        self.assertEqual(self.request(f"/api/meals/{entry['id']}?week=2026-11-23", "DELETE")[0], 400)
        items = self.request("/api/shopping", "POST", {"week": "2026-11-19"})[1]
        self.assertEqual(items[0]["amount"], "1 kg")
        self.assertEqual(self.request(f"/api/meals/{entry['id']}?week=2026-11-19", "DELETE")[0], 200)

    def test_shopping_and_scaling_use_shared_metric_calculations(self):
        first = self.create_recipe()
        second = self.create_recipe({**self.recipe, "ingredients": [
            {"name": "flour", "quantity": 1, "unit": "kg"}]})
        result = self.request("/api/shopping", "POST", {"selections": [
            {"recipe_id": first, "servings": 2}, {"recipe_id": second, "servings": 2}]})[1]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["amount"], "1.5 kg")
        result = self.request(f"/api/recipes/{first}/scale?servings=3")[1]
        self.assertEqual(result[0]["amount"], "750 g")

    def test_boundary_errors_leave_data_untouched(self):
        self.assertEqual(self.request("/api/recipes", "POST", [1])[0], 400)
        self.assertEqual(self.request("/api/meals", "POST", {})[0], 400)
        self.assertEqual(self.request("/api/shopping", "POST", {"selections": [{}]})[0], 400)
        self.assertEqual(self.request("/api/meals?week=oops")[0], 400)
        self.assertEqual(self.request("/api/recipes")[1], [])

    def test_photo_upload_replace_preserve_and_remove(self):
        output = BytesIO()
        with Image.new("RGB", (10, 6), "orange") as image:
            image.save(output, "PNG")
        photo = {"data_url": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode(),
                 "credit": "Recipe photographer", "source_url": "https://example.com/photo"}
        recipe_id = self.create_recipe({**self.recipe, "photo": photo})
        item = self.request("/api/recipes")[1][0]
        self.assertEqual(item["photo_url"], f"/api/recipes/{recipe_id}/photo")
        self.assertEqual(item["photo_credit"], photo["credit"])
        status, first = self.request(item["photo_url"])
        self.assertEqual(status, 200)
        with urlopen(self.base + item["photo_url"]) as response:
            self.assertEqual(response.headers["Content-Type"], "image/jpeg")
        with Image.open(BytesIO(first)) as image:
            self.assertEqual(image.size, (10, 6))
        path = f"/api/recipes/{recipe_id}"
        edited = {**self.recipe, "title": "Edited recipe"}
        self.assertEqual(self.request(path, "PUT", edited)[0], 200)
        self.assertEqual(self.request(item["photo_url"])[1], first)
        self.assertEqual(self.request(path, "PUT", {**edited, "photo": {
            **photo, "credit": "Updated credit"}})[0], 200)
        self.assertEqual(self.request("/api/recipes")[1][0]["photo_credit"], "Updated credit")
        self.assertEqual(self.request(path, "PUT", {**edited, "photo": None})[0], 200)
        self.assertNotIn("photo_url", self.request("/api/recipes")[1][0])
        self.assertEqual(self.request(item["photo_url"])[0], 404)

    def test_invalid_photo_does_not_create_or_overwrite_recipe(self):
        invalid_photo = {"data_url": "data:image/png;base64,aW52YWxpZA=="}
        status, _ = self.request("/api/recipes", "POST", {**self.recipe, "photo": invalid_photo})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("/api/recipes")[1], [])
        recipe_id = self.create_recipe()
        status, _ = self.request(f"/api/recipes/{recipe_id}", "PUT", {
            **self.recipe, "title": "Must not replace title", "photo": invalid_photo})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("/api/recipes")[1][0]["title"], "Pancakes")

    def test_local_only_requests_and_static_allowlist(self):
        for headers in ({"Origin": "https://evil.example"},
                        {"Host": "evil.example"}, {"X-Recipe-Manager": ""}):
            self.assertEqual(self.request("/api/recipes", "POST", self.recipe, headers)[0], 403)
        self.assertEqual(self.request("/api/recipes")[1], [])
        self.assertEqual(self.request("/../storage.py")[0], 404)
        self.assertEqual(self.request("/api/unknown")[0], 404)
        status, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b'lang="en"', html)
        self.assertEqual(self.request("/app.js")[0], 200)
        self.assertEqual(self.request("/styles.css")[0], 200)


if __name__ == "__main__":
    unittest.main()
