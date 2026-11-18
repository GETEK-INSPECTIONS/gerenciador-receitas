"""Readable terminal layouts with optional color and narrow-window fallbacks."""

import os
import shutil
import sys
import textwrap

from .calculations import format_measure, format_quantity


def terminal_width():
    return max(12, min(100, shutil.get_terminal_size((100, 24)).columns - 2))


def _windows_color():
    # Enable VT output as documented by Microsoft for the Windows console.
    # https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel.GetStdHandle(-11)
    mode = wintypes.DWORD()
    return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode))
                and kernel.SetConsoleMode(handle, mode.value | 0x0004))


def color(value, style="accent"):
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return str(value)
    if os.name == "nt" and not _windows_color():
        return str(value)
    codes = {"title": "1;33", "accent": "1;36", "muted": "90", "success": "1;32"}
    return f"\033[{codes.get(style, '0')}m{value}\033[0m"


def _clean(value):
    return " ".join("".join(char for char in str(value)
                           if char.isprintable() or char.isspace()).split())


def render_table(headers, rows, width=None):
    width = max(12, width if width is not None else terminal_width())
    headers = [_clean(header) for header in headers]
    rows = [[_clean(cell) for cell in row] for row in rows]
    if not headers or any(len(row) != len(headers) for row in rows):
        raise ValueError("Each table row must match its headers.")
    if width < 60 or width < len(headers) * 9 + 1:
        lines = []
        for row in rows:
            for label, value in zip(headers, row):
                lines.extend(textwrap.wrap(f"{label}: {value}" if label else value, width) or [""])
            lines.append("-" * width)
        return "\n".join(lines)
    widths = [max(len(header), *(len(row[i]) for row in rows)) if rows else len(header)
              for i, header in enumerate(headers)]
    while sum(widths) + 3 * len(widths) + 1 > width:
        widest = max(range(len(widths)), key=widths.__getitem__)
        widths[widest] -= 1
    border = "+" + "+".join("-" * (size + 2) for size in widths) + "+"
    lines = [border]
    for index, row in enumerate([headers] + rows):
        cells = [textwrap.wrap(cell, size) or [""] for cell, size in zip(row, widths)]
        for line in range(max(map(len, cells))):
            values = [(cell[line] if line < len(cell) else "").ljust(size)
                      for cell, size in zip(cells, widths)]
            lines.append("| " + " | ".join(values) + " |")
        if index == 0:
            lines.append(border)
    lines.append(border)
    return "\n".join(lines)


def heading(title, subtitle=None):
    width = terminal_width()
    print("\n" + color("=" * width, "muted"))
    for line in textwrap.wrap(_clean(title), width):
        print(color(line, "title"))
    if subtitle:
        for line in textwrap.wrap(_clean(subtitle), width):
            print(color(line, "muted"))
    print(color("-" * width, "muted"))


def section(title):
    print("\n" + color(_clean(title), "accent"))


def recipe_table(rows, title="Recipe collection"):
    heading(title, f"{len(rows)} recipes")
    if not rows:
        print("No recipes found.")
        return
    print(render_table(["ID", "Recipe", "Category", "Servings"],
                       [[recipe_id, recipe["title"], recipe.get("category", "Uncategorized"),
                         recipe["servings"]] for recipe_id, recipe in rows]))


def ingredient_table(items, *, shopping=False):
    if shopping:
        rows = [["[ ]", item["name"], format_measure(item["quantity"], item["unit"])]
                for item in items]
        print(render_table(["", "Ingredient", "Total"], rows))
    else:
        rows = [[f"{format_quantity(item['quantity'])} {item['unit']}", item["name"]]
                for item in items]
        print(render_table(["Amount", "Ingredient"], rows))


def main_menu():
    heading("RECIPE MANAGER", "Your collection. Your kitchen. Your week.")
    groups = [
        ("COLLECTION", ["1  Create recipe", "2  List recipes", "3  View recipe", "4  Edit recipe"]),
        ("DISCOVER", ["5  Filter by category", "6  Search by name"]),
        ("PLAN & COOK", ["7  Adjust servings", "8  Build shopping list", "9  Weekly meal planner", "0  Exit"]),
    ]
    if terminal_width() >= 78:
        rows = [[options[index] if index < len(options) else "" for _, options in groups]
                for index in range(4)]
        print(render_table([title for title, _ in groups], rows))
    else:
        for title, options in groups:
            section(title)
            for option in options:
                print("  " + option)
    print(color("Type :cancel inside any form to return without saving.", "muted"))


def pause():
    if sys.stdin.isatty() and sys.stdout.isatty():
        input(color("\nPress Enter to return to the menu... ", "muted"))
