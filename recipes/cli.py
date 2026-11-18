"""Command-line interface for a local recipe notebook."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .model import validate_recipe
from .menu import run_menu
from .storage import delete_recipe, get_recipe, list_recipes, open_database, save_recipe


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gerenciador local de receitas culinárias.")
    parser.add_argument("--db", type=Path, default=Path.home() / ".gerenciador-receitas" / "recipes.db",
                        help="Caminho do banco SQLite (informe antes do comando).")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("menu", help="Abrir o menu interativo para cadastrar e editar receitas.")
    commands.add_parser("list", help="Listar receitas cadastradas.")
    show = commands.add_parser("show", help="Mostrar uma receita em JSON.")
    show.add_argument("id", type=int)
    add = commands.add_parser("add", help="Cadastrar uma receita a partir de um arquivo JSON.")
    add.add_argument("file", type=Path)
    edit = commands.add_parser("edit", help="Substituir os dados de uma receita por um arquivo JSON.")
    edit.add_argument("id", type=int)
    edit.add_argument("file", type=Path)
    delete = commands.add_parser("delete", help="Excluir uma receita após confirmação explícita.")
    delete.add_argument("id", type=int)
    delete.add_argument("--yes", action="store_true", help="Confirmar a exclusão definitiva.")
    args = parser.parse_args(argv)
    if args.command in (None, "menu"):
        return run_menu(args.db)
    try:
        if args.command == "delete" and not args.yes:
            raise ValueError("Para confirmar a exclusão definitiva, repita o comando com --yes.")
        recipe = None
        if args.command in ("add", "edit"):
            recipe = validate_recipe(json.loads(args.file.read_text(encoding="utf-8-sig")))
        with open_database(args.db) as connection:
            if args.command == "list":
                rows = list_recipes(connection)
                output = "\n".join(
                    f"{recipe_id}: {item['title']} ({item['servings']} porções)"
                    for recipe_id, item in rows
                ) or "Nenhuma receita cadastrada."
            elif args.command == "show":
                output = json.dumps(get_recipe(connection, args.id), ensure_ascii=False, indent=2)
            elif args.command in ("add", "edit"):
                recipe_id = save_recipe(connection, recipe, getattr(args, "id", None))
                output = f"Receita {recipe_id} salva."
            else:
                delete_recipe(connection, args.id)
                output = f"Receita {args.id} excluída."
        # Report success only after the transaction has committed.
        print(output)
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
