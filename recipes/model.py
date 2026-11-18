"""Validate the JSON recipe format before anything is written."""

import math


def validate_recipe(value):
    fields = {"title", "servings", "ingredients", "steps"}
    if not isinstance(value, dict) or not fields <= set(value) or set(value) - fields - {"category"}:
        raise ValueError("A recipe must contain title, servings, ingredients and steps; category is optional.")
    if "category" in value and (not isinstance(value["category"], str) or not value["category"].strip()):
        raise ValueError("category must be a non-empty string when provided.")
    title = value["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string.")
    servings = value["servings"]
    if type(servings) is not int or not 1 <= servings <= 10000:
        raise ValueError("servings must be an integer between 1 and 10000.")
    ingredients = value["ingredients"]
    if not isinstance(ingredients, list) or not ingredients:
        raise ValueError("ingredients must contain at least one ingredient.")
    for item in ingredients:
        if not isinstance(item, dict) or set(item) != {"name", "quantity", "unit"}:
            raise ValueError("Each ingredient must contain name, quantity and unit.")
        for key in ("name", "unit"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f"Ingredient {key} must be a non-empty string.")
        quantity = item["quantity"]
        if type(quantity) not in (int, float) or not 0 < quantity <= 1_000_000_000:
            raise ValueError("quantity must be a positive number no greater than 1000000000.")
        if not math.isfinite(quantity):
            raise ValueError("quantity must be finite.")
    steps = value["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps must contain at least one step.")
    if any(not isinstance(step, str) or not step.strip() for step in steps):
        raise ValueError("Each step must be a non-empty string.")
    return value
