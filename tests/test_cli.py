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

    def cli(self, *args, expected=0, input_text=None):
        env = dict(os.environ, PYTHONUTF8="1")
        result = subprocess.run(
            [sys.executable, "-m", "recipes", "--db", str(self.database), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env,
            input=input_text, timeout=10,
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

    def test_menu_creates_recipe_without_json_file(self):
        self.cli(input_text="1\nVitamina\n2\nLeite\n0,5\nl\nBanana\n2\nunidades\n\nBata tudo.\nSirva.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe, {
            "title": "Vitamina", "servings": 2,
            "ingredients": [{"name": "Leite", "quantity": 0.5, "unit": "l"},
                            {"name": "Banana", "quantity": 2, "unit": "unidades"}],
            "steps": ["Bata tudo.", "Sirva."],
        })

    def test_menu_edit_retains_fields_when_enter_is_pressed(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\nPanquecas novas\n\n\n\n\n0\n")
        expected = dict(self.recipe, title="Panquecas novas")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), expected)

    def test_menu_edit_replaces_ingredients_and_steps(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\n\n4\ns\nFarinha\n50\ng\n\ns\nMisture.\nAsse.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe["title"], self.recipe["title"])
        self.assertEqual(recipe["servings"], 4)
        self.assertEqual(recipe["ingredients"], [{"name": "Farinha", "quantity": 50, "unit": "g"}])
        self.assertEqual(recipe["steps"], ["Misture.", "Asse."])

    def test_menu_cancel_does_not_save_partial_edit_or_creation(self):
        self.cli("add", str(self.source))
        self.cli("menu", input_text="4\n1\nOutro título\n4\ns\n:cancelar\n1\nNova\n:cancelar\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), self.recipe)
        self.cli("show", "2", expected=1)

    def test_menu_reprompts_invalid_fields_and_accepts_valid_values(self):
        result = self.cli("menu", input_text="9\n1\n\nSopa\nzero\n0\n10001\n2\n\nÁgua\nnan\ninf\n-1\n1,5\n\nl\n\n\nFerva.\n\n\n0\n")
        recipe = json.loads(self.cli("show", "1").stdout)
        self.assertEqual(recipe["title"], "Sopa")
        self.assertEqual(recipe["servings"], 2)
        self.assertEqual(recipe["ingredients"], [{"name": "Água", "quantity": 1.5, "unit": "l"}])
        self.assertEqual(recipe["steps"], ["Ferva."])
        self.assertNotIn("Traceback", result.stderr)

    def test_menu_eof_keeps_completed_save_but_discards_partial_edit(self):
        self.cli("menu", input_text="1\nChá\n1\nÁgua\n200\nml\n\nFerva.\n\n\n4\n1\nOutro título\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["title"], "Chá")

    def test_menu_lists_and_displays_recipe_in_readable_format(self):
        self.cli("add", str(self.source))
        result = self.cli("menu", input_text="2\n3\n1\n0\n")
        self.assertIn("Panquecas de banana", result.stdout)
        self.assertIn("30 g", result.stdout)
        self.assertIn("Amasse a banana.", result.stdout)
        self.assertNotIn('"ingredients":', result.stdout)

    def test_menu_empty_database_and_missing_recipe_return_to_menu(self):
        result = self.cli("menu", input_text="2\n3\nabc\n-1\n999\n4\n999\n0\n")
        self.assertIn("Nenhuma receita", result.stdout)
        self.assertIn("não encontrada", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_category_is_saved_displayed_and_retained_on_menu_edit(self):
        self.recipe["category"] = "Café da manhã"
        self.write_recipe()
        self.cli("add", str(self.source))
        self.assertIn("Café da manhã", self.cli("list").stdout)
        self.cli("menu", input_text="4\n1\n\n\n\n\n\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout), self.recipe)
        self.assertIn("Categoria: Café da manhã", self.cli("menu", input_text="3\n1\n0\n").stdout)

    def test_category_can_be_added_and_changed_in_menu(self):
        self.cli("menu", input_text="1\nChá\n1\nÁgua\n200\nml\n\nFerva.\n\nBebidas\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["category"], "Bebidas")
        self.cli("menu", input_text="4\n1\n\n\n\n\nCafé da manhã\n0\n")
        self.assertEqual(json.loads(self.cli("show", "1").stdout)["category"], "Café da manhã")

    def test_invalid_category_is_rejected(self):
        for category in ["", " ", 42, None, []]:
            with self.subTest(category=category):
                self.recipe["category"] = category
                self.write_recipe()
                self.cli("add", str(self.source), expected=1)

    def test_example_collection_has_twenty_valid_recipes_in_five_categories(self):
        from recipes.model import validate_recipe

        recipes = json.loads((ROOT / "examples" / "receitas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(recipes), 20)
        self.assertEqual(len({recipe["title"] for recipe in recipes}), 20)
        categories = {recipe["category"] for recipe in recipes}
        self.assertEqual(len(categories), 5)
        for recipe in recipes:
            validate_recipe(recipe)
        for category in categories:
            self.assertEqual(sum(recipe["category"] == category for recipe in recipes), 4)


if __name__ == "__main__":
    unittest.main()
