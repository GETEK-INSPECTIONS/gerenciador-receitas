from contextlib import redirect_stdout
from io import StringIO
import os
import unittest
from unittest.mock import patch

from recipes.display import color, heading, render_table


class DisplayTests(unittest.TestCase):
    def test_table_wraps_long_values_without_dropping_words(self):
        name = "Slow roasted squash with lemon and fresh garden herbs"
        rendered = render_table(["ID", "Recipe", "Category", "Servings"],
                                [[1, name, "Main dishes", 4]], width=70)
        for word in name.split():
            self.assertIn(word, rendered)
        self.assertTrue(all(len(line) <= 70 for line in rendered.splitlines()))
        self.assertIn("Servings", rendered)

    def test_narrow_terminal_uses_readable_stacked_records(self):
        rendered = render_table(["Ingredient", "Amount"],
                                [["extra virgin olive oil", "1.25 L"]], width=28)
        self.assertIn("Ingredient:", rendered)
        self.assertIn("1.25 L", rendered)
        self.assertTrue(all(len(line) <= 28 for line in rendered.splitlines()))

    def test_redirected_output_contains_no_ansi_and_keeps_headings(self):
        stream = StringIO()
        with redirect_stdout(stream):
            heading("Shopping list", "Ready for your next meals")
        self.assertIn("Shopping list", stream.getvalue())
        self.assertNotIn("\x1b", stream.getvalue())

    def test_no_color_overrides_terminal_capability(self):
        class Terminal(StringIO):
            def isatty(self):
                return True
        with patch.dict(os.environ, {"NO_COLOR": "1"}), redirect_stdout(Terminal()):
            self.assertEqual(color("Recipe Manager", "title"), "Recipe Manager")
