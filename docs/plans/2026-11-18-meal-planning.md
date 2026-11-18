# Meal Planning Implementation Plan

**Goal:** Add serving previews, combined shopping lists and persistent weekly meal planning.

**Architecture:** A pure calculation module provides exact ingredient amounts.
SQLite stores dated references to recipes; a separate planning UI integrates with
the existing menu and input helpers.

**Tech Stack:** Python 3.10+, standard library, SQLite, unittest.

**Spec:** docs/specs/2026-11-18-meal-planning.md

## Global Constraints

- English UI, docs, tests and sample data.
- Preserve saved recipe quantities and IDs.
- Test only temporary databases. Back up the personal database before schema changes.
- No external dependencies or unit conversion.

## Review Focus

- Repeating fractions and tiny amounts must not silently become zero.
- Different units/names must not be incorrectly merged.
- Invalid dates and serving counts must not persist.
- Week boundaries and entries in other weeks must remain isolated.
- Cancellation and deletion must not lose saved recipes or plans.

### Task 1: Exact calculations

**Files:** Create recipes/calculations.py and tests/test_calculations.py.
**Interfaces:** scale_ingredients(recipe, servings) -> list of ingredient dicts
with Fraction quantities; shopping_list(selections) consumes (recipe, servings)
pairs; format_quantity(value) -> display string.

- [ ] Write tests asserting 200 g / 4 * 6 = 300 g, 0.1 + 0.2 = 0.3,
  exact thirds, no input mutation, invalid servings, unit separation and aliases.
- [ ] Run the focused tests and observe failure before implementation.
- [ ] Implement Fraction calculations, normalization and explicit approximate display.
- [ ] Run the full suite; expect zero failures.
- [ ] Commit the calculation module and tests.

### Task 2: Persistent weekly plans

**Files:** Modify recipes/storage.py; create recipes/planning.py and tests/test_planning.py.
**Interfaces:** week_start(value) -> Monday date; add_meal(connection, day, meal,
recipe_id, servings) -> ID; list_meals(connection, week) -> entries containing
recipe data; remove_meal(connection, entry_id, week) removes only within that week.

- [ ] Write tests for persisted entries, Monday/Sunday boundaries, duplicate
  meal slots, invalid input rollback, recipe deletion protection, cross-week
  removal refusal and recipe edits reflected in shopping calculations.
- [ ] Run focused tests and observe failures.
- [ ] Enable foreign keys and create a meal_plan table; implement dated operations.
- [ ] Run the full suite; expect zero failures and unchanged legacy recipe behavior.
- [ ] Commit the planner and storage changes.

### Task 3: Menu workflows and documentation

**Files:** Modify recipes/menu.py, tests/test_cli.py and README.md;
create recipes/planning_ui.py.
**Interfaces:** Main menu 7 = serving preview, 8 = shopping list, 9 = weekly planner.
Weekly submenu: 1 view, 2 add, 3 remove, 4 shopping list, 0 back.
Select a week by an ISO date; add entries by weekday and meal number.

- [ ] Add subprocess tests for preview immutability, shopping aggregation,
  planning across restarts, generated weekly shopping lists, invalid input,
  empty weeks and cancellation.
- [ ] Run focused tests and observe failures.
- [ ] Implement prompts using existing read/text/number helpers, display every
  weekday and use short transactions only after input is complete.
- [ ] Document the workflows and limitations; run the full suite.
- [ ] Commit, obtain a fresh code review, fix material issues, then publish and
  open the updated terminal after a personal-database backup.
