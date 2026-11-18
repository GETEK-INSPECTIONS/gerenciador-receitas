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
    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS recipes "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL)"
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
    cursor = connection.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    if cursor.rowcount == 0:
        raise ValueError(f"Recipe {recipe_id} not found.")
