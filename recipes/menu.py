"""Interactive recipe entry using the same validation and storage as the CLI."""

import sqlite3

from .model import validate_recipe
from .storage import get_recipe, list_recipes, open_database, save_recipe


class Cancelled(Exception):
    """The user cancelled the current operation before saving."""


def read(prompt):
    value = input(prompt).strip()
    if value.casefold() == ":cancel":
        raise Cancelled
    return value


def text(prompt, default=None):
    while True:
        value = read(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ")
        if value:
            return value
        if default is not None:
            return default
        print("Enter a non-empty value.")


def number(prompt, maximum, *, integer=False, default=None):
    while True:
        raw = read(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ")
        if not raw and default is not None:
            return default
        try:
            value = int(raw) if integer else float(raw.replace(",", "."))
            if 0 < value <= maximum:
                return value
        except ValueError:
            pass
        kind = "an integer" if integer else "a number"
        print(f"Enter {kind} greater than zero and no greater than {maximum}.")


def replace_list(label):
    while True:
        answer = read(f"Replace {label}? [y/N]: ").casefold()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Enter y for yes or n for no.")


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
    print(f"\n{recipe['title']} — {recipe['servings']} servings")
    print(f"Category: {recipe.get('category', 'Uncategorized')}")
    print("Ingredients:")
    for item in recipe["ingredients"]:
        print(f"  - {item['quantity']} {item['unit']} {item['name']}")
    print("Directions:")
    for index, step in enumerate(recipe["steps"], 1):
        print(f"  {index}. {step}")


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
                print("\n=== Recipe Manager ===\n"
                      "1. Create recipe\n2. List recipes\n"
                      "3. View recipe\n4. Edit recipe\n"
                      "5. Filter by category\n6. Search by name\n0. Exit")
                option = read("Choose an option: ")
                if option == "0":
                    return 0
                if option in ("2", "5", "6"):
                    category, name = None, None
                    if option == "5":
                        with open_database(database) as connection:
                            rows = list_recipes(connection)
                        if not rows:
                            print("No recipes found.")
                            continue
                        labels = {recipe.get("category", "Uncategorized").strip()
                                  for _, recipe in rows}
                        categories = sorted(
                            {label.casefold(): label for label in sorted(labels)}.values(),
                            key=str.casefold,
                        )
                        print("Available categories (type :cancel to return):")
                        for index, label in enumerate(categories, 1):
                            print(f"{index}. {label}")
                        selected = number("Category number", len(categories), integer=True)
                        category = categories[selected - 1]
                    elif option == "6":
                        name = text("Recipe name or part of it (:cancel to return)")
                    with open_database(database) as connection:
                        rows = list_recipes(connection, category=category, name=name)
                    for recipe_id, recipe in rows:
                        print(f"{recipe_id}: {recipe['title']} ({recipe['servings']} servings)"
                              f" — {recipe.get('category', 'Uncategorized')}")
                    if not rows:
                        print("No recipes found.")
                elif option in ("1", "3", "4"):
                    recipe_id, current = None, None
                    if option != "1":
                        recipe_id = number("Recipe ID", 2**63 - 1, integer=True)
                        with open_database(database) as connection:
                            current = get_recipe(connection, recipe_id)
                    if option == "3":
                        show(current)
                        continue
                    # Keep user input outside the transaction; save only a complete form.
                    recipe = edit_form(current)
                    with open_database(database) as connection:
                        recipe_id = save_recipe(connection, recipe, recipe_id)
                    print(f"Recipe {recipe_id} saved.")
                else:
                    print("Invalid option. Choose a number from 0 to 6.")
            except Cancelled:
                print("Operation cancelled. No changes saved.")
            except (OSError, ValueError, sqlite3.Error) as error:
                print(f"Error: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nMenu closed. Previously saved data has been kept.")
        return 0
