from copy import deepcopy
from fractions import Fraction
import unittest

from recipes.calculations import format_quantity, scale_ingredients, shopping_list


def recipe(quantity=200, unit="g", name="rice", servings=4):
    return {"title": "Rice", "servings": servings,
            "ingredients": [{"name": name, "quantity": quantity, "unit": unit}],
            "steps": ["Cook until tender."]}


class CalculationTests(unittest.TestCase):
    def test_scales_up_and_down_without_mutating_recipe(self):
        original = recipe()
        before = deepcopy(original)
        self.assertEqual(scale_ingredients(original, 6)[0]["quantity"], 300)
        self.assertEqual(scale_ingredients(original, 1)[0]["quantity"], 50)
        scaled = scale_ingredients(original, 6)
        scaled[0]["name"] = "different"
        self.assertEqual(original, before)

    def test_repeating_fractions_stay_exact_until_display(self):
        scaled = scale_ingredients(recipe(1, servings=3), 1)
        self.assertEqual(scaled[0]["quantity"], Fraction(1, 3))
        total = shopping_list([(recipe(1, servings=3), 1)] * 3)
        self.assertEqual(total[0]["quantity"], 1)
        self.assertEqual(format_quantity(Fraction(1, 3)), "~0.333333")
        self.assertEqual(format_quantity(Fraction(3, 2)), "1.5")
        self.assertEqual(format_quantity(Fraction(300)), "300")

    def test_decimal_totals_do_not_accumulate_float_error(self):
        items = shopping_list([(recipe(0.1, servings=1), 1), (recipe(0.2, servings=1), 1)])
        self.assertEqual(items[0]["quantity"], Fraction(3, 10))
        self.assertEqual(format_quantity(items[0]["quantity"]), "0.3")

    def test_tiny_amounts_are_not_displayed_as_zero(self):
        amount = scale_ingredients(recipe(5e-324, servings=10000), 1)[0]["quantity"]
        self.assertGreater(Fraction(format_quantity(amount).lstrip("~")), 0)

    def test_normalizes_case_whitespace_and_unit_aliases(self):
        items = shopping_list([(recipe(1, "piece", "  EGG ", 1), 2),
                               (recipe(3, "pieces", "egg", 1), 1),
                               (recipe(10, "grams", "Rice", 1), 1),
                               (recipe(5, "G", " rice ", 1), 1)])
        self.assertEqual([(item["name"].casefold(), item["unit"], item["quantity"])
                          for item in items], [("egg", "piece", 5), ("rice", "g", 15)])

    def test_different_units_and_ingredient_names_remain_separate(self):
        items = shopping_list([(recipe(100, "g", "rice", 1), 1),
                               (recipe(1, "kg", "rice", 1), 1),
                               (recipe(50, "g", "brown rice", 1), 1)])
        self.assertEqual(len(items), 3)
        self.assertEqual({(item["name"], item["unit"]) for item in items},
                         {("rice", "g"), ("rice", "kg"), ("brown rice", "g")})

    def test_invalid_servings_and_source_data_are_rejected(self):
        for servings in (0, -1, 10001, True, 1.5, "2"):
            with self.subTest(servings=servings), self.assertRaises(ValueError):
                scale_ingredients(recipe(), servings)
        with self.assertRaises(ValueError):
            scale_ingredients(recipe(quantity=-1), 2)

    def test_empty_selection_has_no_items(self):
        self.assertEqual(shopping_list([]), [])
