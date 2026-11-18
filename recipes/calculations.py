"""Exact ingredient scaling and shopping-list aggregation."""

from decimal import Decimal, localcontext
from fractions import Fraction

from .model import validate_recipe, validate_servings


UNIT_ALIASES = {
    "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "tablespoon": "tbsp", "tablespoons": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp",
    "pieces": "piece", "cloves": "clove", "leaves": "leaf",
    "slices": "slice", "stalks": "stalk",
}


def scale_ingredients(recipe, servings):
    validate_recipe(recipe)
    validate_servings(servings)
    factor = Fraction(servings, recipe["servings"])
    return [{**item, "quantity": Fraction(str(item["quantity"])) * factor}
            for item in recipe["ingredients"]]


def shopping_list(selections):
    totals = {}
    for recipe, servings in selections:
        for item in scale_ingredients(recipe, servings):
            name = " ".join(item["name"].split())
            unit = " ".join(item["unit"].split())
            # In cooking notation, uppercase T and lowercase t are different units.
            unit = {"T": "tbsp", "t": "tsp"}.get(unit, unit.casefold())
            unit = UNIT_ALIASES.get(unit, unit)
            key = (name.casefold(), unit)
            if key not in totals:
                totals[key] = {"name": name, "unit": unit, "quantity": Fraction(0)}
            totals[key]["quantity"] += item["quantity"]
    return [totals[key] for key in sorted(totals)]


def format_quantity(value):
    quantity = Fraction(str(value))
    with localcontext() as context:
        context.prec = 28
        decimal = Decimal(quantity.numerator) / Decimal(quantity.denominator)
        rounded = Decimal(format(decimal, ".6g")).normalize()
        displayed = format(rounded, "f" if -6 <= rounded.adjusted() < 9 else "g")
    # Calculations remain exact; mark only display rounding as approximate.
    return ("~" if Fraction(displayed) != quantity else "") + displayed
