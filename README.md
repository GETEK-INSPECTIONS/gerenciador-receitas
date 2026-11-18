# Recipe Manager

A local recipe notebook for the terminal, built with Python and SQLite.
Create, list, view, edit and delete recipes with ingredients, quantities, units,
servings, categories and directions. Filter by category or search by name.

## Requirements

Python 3.10 or newer. Only the standard library is required: no packages,
accounts or external services. Run commands from the project root.

## Interactive menu

On Windows:

```powershell
py -3.13 -m recipes
```

On Linux/macOS, replace `py -3.13` with `python3`. With another Python version
on Windows, adjust the launcher version selector.

| Option | Action |
| --- | --- |
| 1 | Create recipe |
| 2 | List recipes |
| 3 | View recipe |
| 4 | Edit recipe |
| 5 | Filter by category |
| 6 | Search by name |
| 0 | Exit |

The form asks for a title, servings, ingredients, directions and an optional category.

- Quantities accept a decimal point or comma, such as `0.5` or `0,5`.
- Leave the next ingredient name or preparation step blank to finish its list.
- While editing, Enter keeps the current title, servings and category.
- Answer `y` to replace all ingredients or all steps; Enter keeps the existing list.
- Type `:cancel` at any prompt to return without saving that operation.
- Completing the form saves immediately. Ctrl+C or end of input closes the menu;
  incomplete forms are discarded and previously saved recipes are kept.

Option **5** displays a numbered list of available categories. Choose a number
to see that category's recipes. Recipes without a category appear under
`Uncategorized`. Option **6** accepts any part of a recipe name.
Matching ignores capitalization and surrounding whitespace. Category matching is
exact; name matching uses a literal substring. Wildcards have no special meaning
and accents remain significant.

You can also open the menu with `py -3.13 -m recipes menu`.

## Direct commands

```powershell
py -3.13 -m recipes --help
py -3.13 -m recipes add examples/pancakes.json
py -3.13 -m recipes list
py -3.13 -m recipes list --category Breakfast
py -3.13 -m recipes list --name pancake
py -3.13 -m recipes list --category Breakfast --name banana
py -3.13 -m recipes show 1
py -3.13 -m recipes edit 1 examples/pancakes.json
py -3.13 -m recipes delete 1 --yes
```

Replace `1` with the ID returned when creating a recipe. To edit with JSON,
copy the example file and change its fields. The `edit` command replaces **all**
fields while keeping the ID. Invalid input does not overwrite the recipe.
Deletion requires `--yes`; omitting it leaves the recipe untouched.

## Recipe format

See [examples/pancakes.json](examples/pancakes.json). Files contain a UTF-8 JSON
object with required fields `title`, `servings`, `ingredients` and `steps`,
plus optional `category`. Older recipes without categories remain valid.

- `title`: a non-empty string.
- `category`: a non-empty string when present; otherwise displayed as `Uncategorized`.
- `servings`: an integer between 1 and 10000.
- `ingredients`: a non-empty list of objects with `name`, `quantity` and `unit`.
- `name` and `unit`: non-empty strings. Units are free text and are not converted.
- `quantity`: a positive, finite number no greater than 1000000000.
  JSON numbers use a decimal point.
- `steps`: a non-empty list of non-empty strings.

Duplicate titles are allowed; each recipe has its own ID. The `show` command
returns recipe data as JSON, suitable for reuse as input.

### Sample collection

[examples/recipes.json](examples/recipes.json) contains 20 recipes, four in each
category: Breakfast, Main dishes, Soups and broths, Snacks, and Desserts.
The collection is for reference and is not loaded automatically.
The `add` command accepts one recipe object per file, not the entire collection.

## Local data

For compatibility with earlier versions, the default database remains at
`~/.gerenciador-receitas/recipes.db` in your home directory.
Place `--db` **before** the command to use a different database:

```powershell
py -3.13 -m recipes --db data/test.db menu
py -3.13 -m recipes --db data/test.db add examples/pancakes.json
py -3.13 -m recipes --db data/test.db list
```

Use the same path in subsequent commands. Back up the SQLite file while the
application is closed. The database is not encrypted; avoid storing sensitive
information. Local database files are ignored by Git.

## Tests

```powershell
py -3.13 -m unittest discover -s tests -v
```

Tests run the real CLI in subprocesses with temporary databases. They cover
persistence, creation, editing, viewing, deletion, confirmation, invalid input,
missing files and IDs, interactive forms, cancellation, categories,
case-insensitive search and empty results.
They do not access or modify your personal database.

Exit codes: `0` for success, `1` for data/storage errors in direct commands,
and `2` for argument syntax errors. The menu displays recoverable errors and
continues running.

## Structure

```text
recipes/
  __main__.py     Program entry point
  cli.py          Direct commands and messages
  menu.py         Interactive menu and forms
  model.py        Recipe validation
  storage.py      SQLite transactions and filtering
examples/        Sample recipes
tests/           CLI integration tests
```

This version runs locally with an interactive menu and optional JSON input.
It does not include a graphical interface, synchronization, unit conversion
or automatic serving adjustments.

## License

Distributed under the [MIT license](LICENSE).