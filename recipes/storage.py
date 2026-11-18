"""SQLite persistence. Mutations are atomic and use parameterized SQL."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3


@contextmanager
def open_database(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS recipes "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS meal_plan ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "day TEXT NOT NULL, "
                "meal TEXT NOT NULL CHECK (meal IN ('Breakfast', 'Lunch', 'Dinner', 'Snack')), "
                "recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT, "
                "servings INTEGER NOT NULL CHECK (servings BETWEEN 1 AND 10000))"
            )
            yield connection
    finally:
        connection.close()


def list_recipes(connection, *, category=None, name=None):
    rows = [(row[0], json.loads(row[1])) for row in
            connection.execute("SELECT id, data FROM recipes ORDER BY id")]
    if category is not None:
        category = category.strip().casefold()
        rows = [(recipe_id, recipe) for recipe_id, recipe in rows
                if recipe.get("category", "Uncategorized").strip().casefold() == category]
    if name is not None:
        name = name.strip().casefold()
        rows = [(recipe_id, recipe) for recipe_id, recipe in rows
                if name in recipe["title"].casefold()]
    return rows


def get_recipe(connection, recipe_id):
    row = connection.execute("SELECT data FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise ValueError(f"Recipe {recipe_id} not found.")
    return json.loads(row[0])


def save_recipe(connection, recipe, recipe_id=None):
    payload = json.dumps(recipe, ensure_ascii=False, allow_nan=False)
    if recipe_id is None:
        return connection.execute("INSERT INTO recipes (data) VALUES (?)", (payload,)).lastrowid
    cursor = connection.execute("UPDATE recipes SET data = ? WHERE id = ?", (payload, recipe_id))
    if cursor.rowcount == 0:
        raise ValueError(f"Recipe {recipe_id} not found.")
    return recipe_id


def delete_recipe(connection, recipe_id):
    if connection.execute("SELECT 1 FROM meal_plan WHERE recipe_id = ? LIMIT 1",
                          (recipe_id,)).fetchone():
        raise ValueError("This recipe has planned meals. Remove those entries before deleting it.")
    cursor = connection.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    if cursor.rowcount == 0:
        raise ValueError(f"Recipe {recipe_id} not found.")
