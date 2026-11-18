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
            "title": "Banana pancakes",
            "servings": 2,
            "ingredients": [
                {"name": "banana", "quantity": 1, "unit": "piece"},
                {"name": "oats", "quantity": 30, "unit": "g"},
            ],
            "steps": ["Mash the banana.", "Mix and cook in a skillet."],
        }
        self.write_recipe()

    def write_recipe(self):
        self.source.write_text(json.dumps(self.recipe, ensure_ascii=False), encoding="utf-8")

    def cli(self, *args, expected=0, input_text=None):
        env = dict(os.environ, PYTHONUTF8="1")
        result = subprocess.run(
            [sys.executable, "-m", "recipes", "--db", str(self.database), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env,
            input=input_text, timeout=10,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if expected == 1:
            self.assertIn("Error:", result.stderr)
        return result

    def test_create_read_update_delete_persists_between_processes(self):
        self.assertIn("1", self.cli("add", str(self.source)).stdout)
        self.assertIn(self.recipe["title"], self.cli("list").stdout)
        saved = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(saved["ingredients"], self.recipe["ingredients"])
        self.recipe["title"] = "Updated pancakes"
        self.write_recipe()
        self.cli("edit", "1", str(self.source))
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], self.recipe["title"])
        self.cli("delete", "1", "--yes")
        self.assertIn("No recipes", self.cli("list").stdout)
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
        self.assertIn("No recipes", self.cli("list").stdout)

    def test_rejects_invalid_ingredient_quantities(self):
        for quantity in [0, -1, True, "two", float("nan"), float("inf")]:
            with self.subTest(quantity=quantity):
                self.recipe["ingredients"][0]["quantity"] = quantity
                self.write_recipe()
                self.cli("add", str(self.source), expected=1)

    def test_malformed_file_and_missing_file_report_errors_without_traceback(self):
        self.source.write_text("{", encoding="utf-8")
        for path in [self.source, self.folder / "missing.json"]:
            result = self.cli("add", str(path), expected=1)
            self.assertIn("Error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_missing_ids_do_not_create_or_delete_other_recipes(self):
        self.cli("add", str(self.source))
        self.cli("edit", "999", str(self.source), expected=1)
        self.cli("delete", "999", "--yes", expected=1)
        self.cli("show", "1")

    def test_title_with_quotes_is_stored_as_data(self):
        self.recipe["title"] = "Baker's bread'); DROP TABLE recipes; --"
        self.write_recipe()
        self.cli("add", str(self.source))
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], self.recipe["title"])
        self.cli("list")

    def test_help_does_not_create_database(self):
        self.assertIn("add", self.cli("--help").stdout)
        self.assertFalse(self.database.exists())

    def test_menu_creates_recipe_without_json_file(self):
        self.cli(input_text="1\nSmoothie\n2\nMilk\n0,5\nl\nBanana\n2\npieces\n\nBlend everything.\nServe.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe, {
            "title": "Smoothie", "servings": 2,
            "ingredients": [{"name": "Milk", "quantity": 0.5, "unit": "l"},
                            {"name": "Banana", "quantity": 2, "unit": "pieces"}],
            "steps": ["Blend everything.", "Serve."],
        })

    def test_menu_edit_retains_fields_when_enter_is_pressed(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\nNew pancakes\n\n\n\n\n0\n")
        expected = dict(self.recipe, title="New pancakes")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), expected)

    def test_menu_edit_replaces_ingredients_and_steps(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\n\n4\ny\nFlour\n50\ng\n\ny\nMix.\nBake.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe["title"], self.recipe["title"])
        self.assertEqual(recipe["servings"], 4)
        self.assertEqual(recipe["ingredients"], [{"name": "Flour", "quantity": 50, "unit": "g"}])
        self.assertEqual(recipe["steps"], ["Mix.", "Bake."])

    def test_menu_cancel_does_not_save_partial_edit_or_creation(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\nAnother title\n4\ny\n:cancel\n1\nNew\n:cancel\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), self.recipe)
        self.cli("show", "2", expected=1)

    def test_menu_reprompts_invalid_fields_and_accepts_valid_values(self):
        result = self.cli("menu", input_text="9\n1\n\nSoup\nzero\n0\n10001\n2\n\nWater\nnan\ninf\n-1\n1,5\n\nl\n\n\nBoil.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe["title"], "Soup")
        self.assertEqual(recipe["servings"], 2)
        self.assertEqual(recipe["ingredients"], [{"name": "Water", "quantity": 1.5, "unit": "l"}])
        self.assertEqual(recipe["steps"], ["Boil."])
        self.assertNotIn("Traceback", result.stderr)

    def test_menu_eof_keeps_completed_save_but_discards_partial_edit(self):
        self.cli("menu", input_text="1\nTea\n1\nWater\n200\nml\n\nBoil.\n\n\n4\n1\nAnother title\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], "Tea")

    def test_menu_lists_and_displays_recipe_in_readable_format(self):
        self.cli("add", str(self.source))
        result = self.cli("menu", input_text="2\n3\n1\n0\n")
        self.assertIn("Banana pancakes", result.stdout)
        self.assertIn("30 g", result.stdout)
        self.assertIn("Mash the banana.", result.stdout)
        self.assertNotIn('"ingredients":', result.stdout)

    def test_menu_empty_database_and_missing_recipe_return_to_menu(self):
        result = self.cli("menu", input_text="2\n3\nabc\n-1\n999\n4\n999\n0\n")
        self.assertIn("No recipes", result.stdout)
        self.assertIn("not found", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_category_is_saved_displayed_and_retained_on_menu_edit(self):
        self.recipe["category"] = "Breakfast"
        self.write_recipe()
        self.cli("add", str(self.source))
        self.assertIn("Breakfast", self.cli("list").stdout)
        self.cli("menu", input_text="4\n1\n\n\n\n\n\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), self.recipe)
        self.assertIn("Category: Breakfast", self.cli("menu", input_text="3\n1\n0\n").stdout)

    def test_category_can_be_added_and_changed_in_menu(self):
        self.cli("menu", input_text="1\nTea\n1\nWater\n200\nml\n\nBoil.\n\nDrinks\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["category"], "Drinks")
        self.cli("menu", input_text="4\n1\n\n\n\n\nBreakfast\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["category"], "Breakfast")

    def test_invalid_category_is_rejected(self):
        for category in ["", " ", 42, None, []]:
            with self.subTest(category=category):
                self.recipe["category"] = category
                self.write_recipe()
                self.cli("add", str(self.source), expected=1)

    def test_example_collection_has_twenty_valid_recipes_in_five_categories(self):
        from recipes.model import validate_recipe

        recipes = json.loads((ROOT / "examples" / "recipes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(recipes), 20)
        self.assertEqual(len({recipe["title"] for recipe in recipes}), 20)
        categories = {recipe["category"] for recipe in recipes}
        self.assertEqual(len(categories), 5)
        for recipe in recipes:
            validate_recipe(recipe)
        for category in categories:
            self.assertEqual(sum(recipe["category"] == category for recipe in recipes), 4)

    def test_list_filters_category_and_partial_name_together(self):
        for title, category in [("Banana pancakes", "Breakfast"),
                                ("Banana cake", "Desserts"), ("Scrambled eggs", "Breakfast")]:
            self.recipe.update(title=title, category=category)
            self.write_recipe()
            self.cli("add", str(self.source))
        result = self.cli("list", "--category", " breakfast ", "--name", " BANANA ")
        self.assertIn("Banana pancakes", result.stdout)
        self.assertNotIn("Banana cake", result.stdout)
        self.assertNotIn("Scrambled eggs", result.stdout)
        self.assertIn("No recipes found.", self.cli("list", "--name", "%").stdout)
        self.assertIn("No recipes found.", self.cli("list", "--category", "Break").stdout)

    def test_menu_filters_category_and_searches_partial_name(self):
        for title, category in [("Banana pancakes", "Breakfast"), ("Lentil soup", "Soups")]:
            self.recipe.update(title=title, category=category)
            self.write_recipe()
            self.cli("add", str(self.source))
        filtered = self.cli("menu", input_text="5\n99\n1\n0\n")
        self.assertIn("Banana pancakes", filtered.stdout)
        self.assertNotIn("Lentil soup", filtered.stdout)
        found = self.cli("menu", input_text="6\n\n pAnCaKe \n0\n")
        self.assertIn("Banana pancakes", found.stdout)
        self.assertNotIn("Lentil soup", found.stdout)

    def test_menu_handles_empty_filters_missing_results_and_cancellation(self):
        empty = self.cli("menu", input_text="5\n6\nmissing\n0\n")
        self.assertIn("No recipes found.", empty.stdout)
        self.cli("add", str(self.source))
        cancelled = self.cli("menu", input_text="5\n:cancel\n6\n:cancel\n6\nmissing\n0\n")
        self.assertIn("Operation cancelled.", cancelled.stdout)
        self.assertIn("No recipes found.", cancelled.stdout)
        self.assertEqual(json.loads(self.cli("show", "1").stdout), self.recipe)

    def test_category_filter_includes_uncategorized_legacy_recipes(self):
        self.cli("add", str(self.source))
        self.assertIn("Banana pancakes", self.cli("list", "--category", "uncategorized").stdout)
        filtered = self.cli("menu", input_text="5\n1\n0\n")
        self.assertIn("Banana pancakes", filtered.stdout)

    def test_name_search_casefolds_unicode_and_treats_quotes_literally(self):
        self.recipe["title"] = "Crème brûlée"
        self.write_recipe()
        self.cli("add", str(self.source))
        self.assertIn("Crème brûlée", self.cli("list", "--name", "CRÈME").stdout)
        self.assertIn("No recipes found.", self.cli("list", "--name", "' OR 1=1 --").stdout)


if __name__ == "__main__":
    unittest.main()
