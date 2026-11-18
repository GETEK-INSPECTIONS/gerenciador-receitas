"""Serving previews, shopping selections and the weekly planner menu."""

from datetime import date, timedelta
import sqlite3

from .calculations import scale_ingredients, shopping_list
from .display import heading, ingredient_table, pause, recipe_table, render_table
from .planning import MEALS, WEEKDAYS, add_meal, list_meals, remove_meal, week_start
from .prompts import Cancelled, number, read, text
from .storage import get_recipe, list_recipes, open_database


def recipe_choices(database):
    with open_database(database) as connection:
        recipes = list_recipes(connection)
    if not recipes:
        print("No recipes found.")
        return False
    recipe_table(recipes, "Choose a recipe")
    return True


def serving_preview(database):
    if not recipe_choices(database):
        return
    recipe_id = number("Recipe ID (:cancel to return)", 2**63 - 1, integer=True)
    with open_database(database) as connection:
        recipe = get_recipe(connection, recipe_id)
    servings = number("Target servings", 10000, integer=True, default=recipe["servings"])
    heading(recipe["title"], f"Serving preview | Original: {recipe['servings']} | Target: {servings}")
    ingredient_table(scale_ingredients(recipe, servings))
    print("Preview only: the saved recipe is unchanged.")
    print("~ marks rounded amounts. Cooking times are not automatically adjusted.")


def show_shopping_list(selections):
    items = shopping_list(selections)
    if not items:
        print("No ingredients selected.")
        return
    heading("SHOPPING LIST", f"{len(selections)} recipe selections | Ready for your next meals")
    ingredient_table(items, shopping=True)
    print(f"{len(items)} ingredient lines. ~ marks rounded amounts.")
    print("Metric totals combine g/kg and ml/L. Other unit families remain separate.")


def shopping_menu(database):
    if not recipe_choices(database):
        return
    selections = []
    print("Add recipes one at a time. Repeated selections count as additional meals.")
    while True:
        raw = read("Recipe ID (Enter to finish; :cancel to discard the list): ")
        if not raw:
            break
        try:
            recipe_id = int(raw)
            if not 1 <= recipe_id <= 2**63 - 1:
                raise ValueError("Recipe ID must be a positive integer.")
            with open_database(database) as connection:
                recipe = get_recipe(connection, recipe_id)
        except ValueError as error:
            print(f"Error: {error}")
            continue
        servings = number("Servings", 10000, integer=True, default=recipe["servings"])
        selections.append((recipe, servings))
        print(f"Added: {recipe['title']} — {servings} servings.")
    show_shopping_list(selections)


def choose_week(default=None):
    while True:
        raw = text("Date in desired week (YYYY-MM-DD; :cancel to return)",
                   (default or date.today()).isoformat())
        try:
            return week_start(raw)
        except ValueError as error:
            print(f"Error: {error}")


def show_week(entries, start):
    heading("WEEKLY MEAL PLAN", f"{start} to {start + timedelta(days=6)} | {len(entries)} meals")
    if not entries:
        print("No meals planned for this week.")
    rows = []
    for offset, weekday in enumerate(WEEKDAYS):
        day = (start + timedelta(days=offset)).isoformat()
        scheduled = [entry for entry in entries if entry["day"] == day]
        for index, entry in enumerate(scheduled):
            rows.append([f"{weekday} {day}" if index == 0 else "",
                         f"#{entry['id']} {entry['meal']}: {entry['recipe']['title']}"
                         f" / {entry['servings']} servings"])
        if not scheduled:
            rows.append([f"{weekday} {day}", "(no meals)"])
    print(render_table(["Day", "Planned meals"], rows))


def confirm_removal(entry_id):
    while True:
        answer = read(f"Remove meal entry #{entry_id}? [y/N]: ").casefold()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Enter y for yes or n for no.")


def weekly_menu(database):
    start = choose_week()
    while True:
        try:
            end = start + timedelta(days=6)
            heading("WEEKLY PLANNER", f"{start} to {end}")
            print(render_table(["Key", "Action"], [
                [1, "View week"], [2, "Add meal"], [3, "Remove meal"],
                [4, "Weekly shopping list"], [5, "Change week"], [0, "Back"]]))
            option = read("Choose an option: ")
            if option == "0":
                return
            if option == "5":
                start = choose_week(start)
                continue
            if option in ("1", "3", "4"):
                with open_database(database) as connection:
                    entries = list_meals(connection, start)
                if option == "1":
                    show_week(entries, start)
                elif not entries:
                    print("No meals planned for this week.")
                elif option == "4":
                    print(f"Week of {start}: {len(entries)} planned meal entries.")
                    show_shopping_list([(entry["recipe"], entry["servings"]) for entry in entries])
                else:
                    show_week(entries, start)
                    entry_id = number("Meal entry ID", 2**63 - 1, integer=True)
                    if not any(entry["id"] == entry_id for entry in entries):
                        raise ValueError("Meal entry not found in this week.")
                    if confirm_removal(entry_id):
                        with open_database(database) as connection:
                            remove_meal(connection, entry_id, start)
                        print(f"Meal entry #{entry_id} removed.")
                    else:
                        print("Meal entry kept.")
                pause()
            elif option == "2":
                if not recipe_choices(database):
                    continue
                for index, weekday in enumerate(WEEKDAYS, 1):
                    print(f"{index}. {weekday} {(start + timedelta(days=index - 1)).isoformat()}")
                day = start + timedelta(days=number("Day number", 7, integer=True) - 1)
                for index, meal in enumerate(MEALS, 1):
                    print(f"{index}. {meal}")
                meal = MEALS[number("Meal number", len(MEALS), integer=True) - 1]
                recipe_id = number("Recipe ID", 2**63 - 1, integer=True)
                with open_database(database) as connection:
                    recipe = get_recipe(connection, recipe_id)
                servings = number("Servings", 10000, integer=True, default=recipe["servings"])
                with open_database(database) as connection:
                    entry_id = add_meal(connection, day, meal, recipe_id, servings)
                print(f"Meal entry #{entry_id} saved: {day}, {meal}, {servings} servings.")
            else:
                print("Invalid option. Choose a number from 0 to 5.")
        except Cancelled:
            print("Operation cancelled. No changes saved.")
        except (OSError, ValueError, sqlite3.Error) as error:
            print(f"Error: {error}")
