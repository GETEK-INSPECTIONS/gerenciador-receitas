"""Interactive recipe entry using the same validation and storage as the CLI."""

import sqlite3

from .model import validate_recipe
from .prompts import Cancelled, number, read, replace_list, text
from .planning_ui import serving_preview, shopping_menu, weekly_menu
from .display import color, heading, ingredient_table, main_menu, pause, recipe_table, render_table, section
from .storage import get_recipe, list_recipes, open_database, save_recipe


def ingredients():
    print("Ingredients: enter one at a time. Leave the name blank to finish.")
    items = []
    while True:
        name = read("Ingredient name: ")
        if not name:
            if items:
                return items
            print("Enter at least one ingredient.")
            continue
        quantity = number("Quantity (decimal point or comma)", 1_000_000_000)
        unit = text("Unit (e.g. g, ml, piece)")
        items.append({"name": name, "quantity": quantity, "unit": unit})


def steps():
    print("Directions: enter one step per line. Leave a line blank to finish.")
    items = []
    while True:
        step = read(f"Step {len(items) + 1}: ")
        if step:
            items.append(step)
        elif items:
            return items
        else:
            print("Enter at least one step.")


def show(recipe):
    heading(recipe["title"],
            f"{recipe['servings']} servings | Category: {recipe.get('category', 'Uncategorized')}")
    section("INGREDIENTS")
    ingredient_table(recipe["ingredients"])
    section("DIRECTIONS")
    print(render_table(["Step", "Directions"], list(enumerate(recipe["steps"], 1))))


def edit_form(current=None):
    print("\nType :cancel at any prompt to return without saving.")
    if current is not None:
        show(current)
        print("Press Enter to keep the current values.")
    previous = current or {}
    title = text("Title", previous.get("title"))
    servings = number("Servings", 10000, integer=True, default=previous.get("servings"))
    items = ingredients() if current is None or replace_list("ingredients") else current["ingredients"]
    preparation = steps() if current is None or replace_list("steps") else current["steps"]
    category = text("Category (Enter keeps the current value; optional if uncategorized)", previous.get("category", ""))
    recipe = {"title": title, "servings": servings, "ingredients": items, "steps": preparation}
    if category:
        recipe["category"] = category
    return validate_recipe(recipe)


def run_menu(database):
    try:
        while True:
            try:
                main_menu()
                option = read("Choose an option: ")
                if option == "0":
                    return 0
                if option in ("7", "8", "9"):
                    {"7": serving_preview, "8": shopping_menu, "9": weekly_menu}[option](database)
                    if option != "9":
                        pause()
                    continue
                if option in ("2", "5", "6"):
                    category, name = None, None
                    if option == "5":
                        with open_database(database) as connection:
                            rows = list_recipes(connection)
                        if not rows:
                            print("No recipes found.")
                            pause()
                            continue
                        labels = {recipe.get("category", "Uncategorized").strip()
                                  for _, recipe in rows}
                        categories = sorted(
                            {label.casefold(): label for label in sorted(labels)}.values(),
                            key=str.casefold,
                        )
                        heading("Browse categories", "Choose a number or type :cancel to return")
                        print(render_table(["Key", "Category"], list(enumerate(categories, 1))))
                        selected = number("Category number", len(categories), integer=True)
                        category = categories[selected - 1]
                    elif option == "6":
                        name = text("Recipe name or part of it (:cancel to return)")
                    with open_database(database) as connection:
                        rows = list_recipes(connection, category=category, name=name)
                    title = f"Category: {category}" if category else f"Search: {name}" if name else "Recipe collection"
                    recipe_table(rows, title)
                elif option in ("1", "3", "4"):
                    recipe_id, current = None, None
                    if option != "1":
                        recipe_id = number("Recipe ID", 2**63 - 1, integer=True)
                        with open_database(database) as connection:
                            current = get_recipe(connection, recipe_id)
                    if option == "3":
                        show(current)
                        pause()
                        continue
                    # Keep user input outside the transaction; save only a complete form.
                    recipe = edit_form(current)
                    with open_database(database) as connection:
                        recipe_id = save_recipe(connection, recipe, recipe_id)
                    print(color(f"Recipe {recipe_id} saved.", "success"))
                else:
                    print("Invalid option. Choose a number from 0 to 9.")
            except Cancelled:
                print("Operation cancelled. No changes saved.")
            except (OSError, ValueError, sqlite3.Error) as error:
                print(f"Error: {error}")
            pause()
    except (EOFError, KeyboardInterrupt):
        print("\nMenu closed. Previously saved data has been kept.")
        return 0
