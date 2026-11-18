# Recipe Manager

- Keep application messages, source comments, documentation, tests and sample
  recipes in English. Conversation with the user may remain in Portuguese.
- Use Python's standard library unless a dependency is explicitly justified.
- Preserve existing recipe IDs and data when changing storage.
- Back up the user's database before a bulk data migration.
- Test behavior with temporary databases, never the user's personal database.
- Run `py -3.13 -m unittest discover -s tests -v` on Windows or
  `python3 -m unittest discover -s tests -v` on Linux/macOS before publishing changes.
