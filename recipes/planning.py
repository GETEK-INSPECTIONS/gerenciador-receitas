"""Calendar validation and persistent meal-plan operations."""

from datetime import date, timedelta
import json

from .model import validate_servings
from .storage import get_recipe


MEALS = ("Breakfast", "Lunch", "Dinner", "Snack")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def parse_date(value):
    if type(value) is date:
        return value
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from None


def week_start(value):
    parsed = parse_date(value)
    monday = parsed - timedelta(days=parsed.weekday())
    try:
        monday + timedelta(days=6)
    except OverflowError:
        raise ValueError("Choose a date within a complete Monday-Sunday week.") from None
    return monday


def add_meal(connection, day, meal, recipe_id, servings):
    day = parse_date(day)
    week_start(day)
    if not isinstance(meal, str) or meal.strip().title() not in MEALS:
        raise ValueError("Choose Breakfast, Lunch, Dinner or Snack.")
    validate_servings(servings)
    if type(recipe_id) is not int or not 1 <= recipe_id <= 2**63 - 1:
        raise ValueError("Recipe ID must be a positive integer.")
    get_recipe(connection, recipe_id)
    return connection.execute(
        "INSERT INTO meal_plan (day, meal, recipe_id, servings) VALUES (?, ?, ?, ?)",
        (day.isoformat(), meal.strip().title(), recipe_id, servings),
    ).lastrowid


def list_meals(connection, week):
    start = week_start(week)
    end = start + timedelta(days=6)
    rows = connection.execute(
        "SELECT p.id, p.day, p.meal, p.recipe_id, p.servings, r.data "
        "FROM meal_plan AS p JOIN recipes AS r ON r.id = p.recipe_id "
        "WHERE p.day BETWEEN ? AND ? "
        "ORDER BY p.day, CASE p.meal WHEN 'Breakfast' THEN 1 WHEN 'Lunch' THEN 2 "
        "WHEN 'Dinner' THEN 3 ELSE 4 END, p.id",
        (start.isoformat(), end.isoformat()),
    )
    return [{"id": row[0], "day": row[1], "meal": row[2], "recipe_id": row[3],
             "servings": row[4], "recipe": json.loads(row[5])} for row in rows]


def remove_meal(connection, entry_id, week):
    if type(entry_id) is not int or not 1 <= entry_id <= 2**63 - 1:
        raise ValueError("Entry ID must be a positive integer.")
    start = week_start(week)
    end = start + timedelta(days=6)
    cursor = connection.execute(
        "DELETE FROM meal_plan WHERE id = ? AND day BETWEEN ? AND ?",
        (entry_id, start.isoformat(), end.isoformat()),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"Meal entry {entry_id} not found in the selected week.")
