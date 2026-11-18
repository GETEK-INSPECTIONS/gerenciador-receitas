from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from recipes.calculations import shopping_list
from recipes.planning import add_meal, list_meals, remove_meal, week_start
from recipes.storage import delete_recipe, get_recipe, open_database, save_recipe


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "recipes.db"
        self.recipe = {"title": "Rice", "servings": 4,
                       "ingredients": [{"name": "rice", "quantity": 200, "unit": "g"}],
                       "steps": ["Cook."]}
        with open_database(self.path) as connection:
            self.recipe_id = save_recipe(connection, self.recipe)

    def test_plan_persists_and_limits_results_to_monday_through_sunday(self):
        with open_database(self.path) as connection:
            first = add_meal(connection, "2026-11-16", "lunch", self.recipe_id, 6)
            last = add_meal(connection, "2026-11-22", "Dinner", self.recipe_id, 2)
            add_meal(connection, "2026-11-23", "lunch", self.recipe_id, 4)
        with open_database(self.path) as connection:
            entries = list_meals(connection, "2026-11-18")
        self.assertEqual(week_start("2026-11-22"), date(2026, 11, 16))
        self.assertEqual([entry["id"] for entry in entries], [first, last])
        self.assertEqual(entries[0]["servings"], 6)
        self.assertEqual(entries[0]["recipe"], self.recipe)

    def test_multiple_recipes_can_share_one_meal_slot(self):
        with open_database(self.path) as connection:
            add_meal(connection, "2026-11-16", "Lunch", self.recipe_id, 1)
            add_meal(connection, "2026-11-16", "Lunch", self.recipe_id, 2)
            self.assertEqual(len(list_meals(connection, "2026-11-16")), 2)

    def test_invalid_entries_never_persist(self):
        cases = [("2026-02-30", "Lunch", self.recipe_id, 2),
                 ("20261118", "Lunch", self.recipe_id, 2),
                 ("9999-12-31", "Lunch", self.recipe_id, 2),
                 ("2026-11-18", "Brunch", self.recipe_id, 2),
                 ("2026-11-18", "Lunch", 999, 2),
                 ("2026-11-18", "Lunch", self.recipe_id, 0),
                 ("2026-11-18", "Lunch", self.recipe_id, True)]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                with open_database(self.path) as connection:
                    add_meal(connection, *args)
        with open_database(self.path) as connection:
            self.assertEqual(list_meals(connection, "2026-11-18"), [])

    def test_removal_is_scoped_to_selected_week(self):
        with open_database(self.path) as connection:
            entry_id = add_meal(connection, "2026-11-23", "Dinner", self.recipe_id, 2)
        with self.assertRaises(ValueError):
            with open_database(self.path) as connection:
                remove_meal(connection, entry_id, "2026-11-16")
        with open_database(self.path) as connection:
            self.assertEqual(len(list_meals(connection, "2026-11-23")), 1)
            remove_meal(connection, entry_id, "2026-11-23")
        with open_database(self.path) as connection:
            self.assertEqual(list_meals(connection, "2026-11-23"), [])
            self.assertEqual(get_recipe(connection, self.recipe_id), self.recipe)

    def test_planned_recipe_deletion_is_blocked_until_entry_removed(self):
        with open_database(self.path) as connection:
            entry_id = add_meal(connection, "2026-11-18", "Lunch", self.recipe_id, 2)
        with self.assertRaisesRegex(ValueError, "planned"):
            with open_database(self.path) as connection:
                delete_recipe(connection, self.recipe_id)
        with open_database(self.path) as connection:
            self.assertEqual(get_recipe(connection, self.recipe_id), self.recipe)
            remove_meal(connection, entry_id, "2026-11-18")
            delete_recipe(connection, self.recipe_id)

    def test_database_foreign_key_also_prevents_orphaned_plan_entries(self):
        with open_database(self.path) as connection:
            add_meal(connection, "2026-11-18", "Lunch", self.recipe_id, 2)
        with self.assertRaises(sqlite3.IntegrityError):
            with open_database(self.path) as connection:
                connection.execute("DELETE FROM recipes WHERE id = ?", (self.recipe_id,))

    def test_recipe_edits_are_reflected_in_weekly_shopping_list(self):
        with open_database(self.path) as connection:
            add_meal(connection, "2026-11-18", "Lunch", self.recipe_id, 6)
            self.recipe["ingredients"][0]["quantity"] = 100
            save_recipe(connection, self.recipe, self.recipe_id)
        with open_database(self.path) as connection:
            entries = list_meals(connection, "2026-11-18")
        items = shopping_list([(entry["recipe"], entry["servings"]) for entry in entries])
        self.assertEqual(items[0]["quantity"], 150)

    def test_legacy_database_recipes_are_preserved_when_schema_is_added(self):
        legacy_path = Path(self.temp.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        connection.execute("CREATE TABLE recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)")
        connection.execute("INSERT INTO recipes (id, data) VALUES (42, ?)", (json.dumps(self.recipe),))
        connection.commit()
        connection.close()
        with open_database(legacy_path) as connection:
            self.assertEqual(get_recipe(connection, 42), self.recipe)
            self.assertEqual(list_meals(connection, "2026-11-18"), [])
