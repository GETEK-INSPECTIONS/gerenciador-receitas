"""Command-line interface for a local recipe notebook."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .model import validate_recipe
from .menu import run_menu
from .storage import delete_recipe, get_recipe, list_recipes, open_database, save_recipe


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local recipe manager.")
    parser.add_argument("--db", type=Path, default=Path.home() / ".gerenciador-receitas" / "recipes.db",
                        help="SQLite database path (place before the command).")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("menu", help="Open the interactive menu to create and edit recipes.")
    listing = commands.add_parser("list", help="List saved recipes.")
    listing.add_argument("--category", help="Filter by exact category, ignoring case.")
    listing.add_argument("--name", help="Search for part of a recipe name, ignoring case.")
    show = commands.add_parser("show", help="Show a recipe as JSON.")
    show.add_argument("id", type=int)
    add = commands.add_parser("add", help="Create a recipe from a JSON file.")
    add.add_argument("file", type=Path)
    edit = commands.add_parser("edit", help="Replace a recipe using a JSON file.")
    edit.add_argument("id", type=int)
    edit.add_argument("file", type=Path)
    delete = commands.add_parser("delete", help="Delete a recipe after explicit confirmation.")
    delete.add_argument("id", type=int)
    delete.add_argument("--yes", action="store_true", help="Confirm permanent deletion.")
    args = parser.parse_args(argv)
    if args.command in (None, "menu"):
        return run_menu(args.db)
    try:
        if args.command == "delete" and not args.yes:
            raise ValueError("To confirm permanent deletion, repeat the command with --yes.")
        recipe = None
        if args.command in ("add", "edit"):
            recipe = validate_recipe(json.loads(args.file.read_text(encoding="utf-8-sig")))
        with open_database(args.db) as connection:
            if args.command == "list":
                rows = list_recipes(connection, category=args.category, name=args.name)
                output = "\n".join(
                    f"{recipe_id}: {item['title']} ({item['servings']} servings)"
                    f" — {item.get('category', 'Uncategorized')}"
                    for recipe_id, item in rows
                ) or "No recipes found."
            elif args.command == "show":
                output = json.dumps(get_recipe(connection, args.id), ensure_ascii=False, indent=2)
            elif args.command in ("add", "edit"):
                recipe_id = save_recipe(connection, recipe, getattr(args, "id", None))
                output = f"Recipe {recipe_id} saved."
            else:
                delete_recipe(connection, args.id)
                output = f"Recipe {args.id} deleted."
        # Report success only after the transaction has committed.
        print(output)
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
