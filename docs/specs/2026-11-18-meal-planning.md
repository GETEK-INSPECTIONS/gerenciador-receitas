# Serving sizes, shopping lists and weekly planning

The user approved implementing these three connected features in the existing
English terminal application. Continue using Python 3.10+ and the standard library.

- Preview ingredients for 1–10000 servings without modifying the saved recipe.
- Build a shopping list from multiple recipes, each with its own serving count.
  Sum ingredients whose names and units match after case/whitespace normalization.
  Recognize common unit spelling aliases but do not convert mass or volume units,
  or merge ingredients that have different names.
- Save meal entries by calendar date, meal (Breakfast/Lunch/Dinner/Snack), recipe
  and servings. Multiple entries per day/meal are allowed.
- Show a Monday–Sunday week, add/remove entries and build its shopping list.
- Plans reference current recipes, so recipe edits affect future shopping lists.
  Prevent deleting a recipe while it is referenced by a meal entry.
- Preserve recipe IDs/data. Add an SQLite table without changing existing rows.
- English UI/docs/tests; Portuguese conversation. All operations support the
  existing cancellation flow and errors must not leave partially saved entries.
- Back up the personal database before enabling the new schema. Never use the
  personal database for tests.

Implementation choices: exact Fraction arithmetic for ingredient calculations;
decimal display rounded to six significant digits with an approximation marker
when necessary; an unsaved shopping-list selection and persistent weekly plans.
