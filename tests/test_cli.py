import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipeCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.database = self.folder / "recipes.db"
        self.source = self.folder / "recipe.json"
        self.recipe = {
            "title": "Panquecas de banana",
            "servings": 2,
            "ingredients": [
                {"name": "banana", "quantity": 1, "unit": "unidade"},
                {"name": "aveia", "quantity": 30, "unit": "g"},
            ],
            "steps": ["Amasse a banana.", "Misture e cozinhe na frigideira."],
        }
        self.write_recipe()

    def write_recipe(self):
        self.source.write_text(json.dumps(self.recipe, ensure_ascii=False), encoding="utf-8")

    def cli(self, *args, expected=0):
        env = dict(os.environ, PYTHONUTF8="1")
        result = subprocess.run(
            [sys.executable, "-m", "recipes", "--db", str(self.database), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if expected == 1:
            self.assertIn("Erro:", result.stderr)
        return result

    def test_create_read_update_delete_persists_between_processes(self):
        self.assertIn("1", self.cli("add", str(self.source)).stdout)
        self.assertIn(self.recipe["title"], self.cli("list").stdout)
        saved = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(saved["ingredients"], self.recipe["ingredients"])
        self.recipe["title"] = "Panquecas revisadas"
        self.write_recipe()
        self.cli("edit", "1", str(self.source))
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], self.recipe["title"])
        self.cli("delete", "1", "--yes")
        self.assertIn("Nenhuma", self.cli("list").stdout)
        self.cli("show", "1", expected=1)

    def test_delete_requires_confirmation_and_preserves_recipe(self):
        self.cli("add", str(self.source))
        self.assertIn("--yes", self.cli("delete", "1", expected=1).stderr)
        self.cli("show", "1")

    def test_invalid_edit_keeps_previous_recipe(self):
        self.cli("add", str(self.source))
        self.recipe["servings"] = 0
        self.write_recipe()
        self.cli("edit", "1", str(self.source), expected=1)
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["servings"], 2)

    def test_rejects_invalid_recipe_fields(self):
        for key, value in [("title", " "), ("servings", True), ("servings", 1.5),
                           ("ingredients", []), ("steps", [""]), ("unknown", "field")]:
            with self.subTest(key=key, value=value):
                invalid = dict(self.recipe, **{key: value})
                self.source.write_text(json.dumps(invalid), encoding="utf-8")
                self.cli("add", str(self.source), expected=1)
        self.assertIn("Nenhuma", self.cli("list").stdout)

    def test_rejects_invalid_ingredient_quantities(self):
        for quantity in [0, -1, True, "dois", float("nan"), float("inf")]:
            with self.subTest(quantity=quantity):
                self.recipe["ingredients"][0]["quantity"] = quantity
                self.write_recipe()
                self.cli("add", str(self.source), expected=1)

    def test_malformed_file_and_missing_file_report_errors_without_traceback(self):
        self.source.write_text("{", encoding="utf-8")
        for path in [self.source, self.folder / "missing.json"]:
            result = self.cli("add", str(path), expected=1)
            self.assertIn("Erro:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_missing_ids_do_not_create_or_delete_other_recipes(self):
        self.cli("add", str(self.source))
        self.cli("edit", "999", str(self.source), expected=1)
        self.cli("delete", "999", "--yes", expected=1)
        self.cli("show", "1")

    def test_title_with_quotes_is_stored_as_data(self):
        self.recipe["title"] = "Pão d'água'); DROP TABLE recipes; --"
        self.write_recipe()
        self.cli("add", str(self.source))
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], self.recipe["title"])
        self.cli("list")

    def test_help_does_not_create_database(self):
        self.assertIn("add", self.cli("--help").stdout)
        self.assertFalse(self.database.exists())


if __name__ == "__main__":
    unittest.main()
