"""Validate the JSON recipe format before anything is written."""

import math


def validate_recipe(value):
    fields = {"title", "servings", "ingredients", "steps"}
    if not isinstance(value, dict) or not fields <= set(value) or set(value) - fields - {"category"}:
        raise ValueError("A receita deve conter title, servings, ingredients e steps; category é opcional.")
    if "category" in value and (not isinstance(value["category"], str) or not value["category"].strip()):
        raise ValueError("category deve ser um texto não vazio, quando informado.")
    title = value["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title deve ser um texto não vazio.")
    servings = value["servings"]
    if type(servings) is not int or not 1 <= servings <= 10000:
        raise ValueError("servings deve ser um inteiro entre 1 e 10000.")
    ingredients = value["ingredients"]
    if not isinstance(ingredients, list) or not ingredients:
        raise ValueError("ingredients deve conter pelo menos um ingrediente.")
    for item in ingredients:
        if not isinstance(item, dict) or set(item) != {"name", "quantity", "unit"}:
            raise ValueError("Cada ingrediente deve conter name, quantity e unit.")
        for key in ("name", "unit"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f"{key} do ingrediente deve ser um texto não vazio.")
        quantity = item["quantity"]
        if type(quantity) not in (int, float) or not 0 < quantity <= 1_000_000_000:
            raise ValueError("quantity deve ser um número positivo de até 1000000000.")
        if not math.isfinite(quantity):
            raise ValueError("quantity deve ser finito.")
    steps = value["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps deve conter pelo menos uma etapa.")
    if any(not isinstance(step, str) or not step.strip() for step in steps):
        raise ValueError("Cada etapa deve ser um texto não vazio.")
    return value
