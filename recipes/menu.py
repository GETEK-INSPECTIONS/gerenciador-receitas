"""Interactive recipe entry using the same validation and storage as the CLI."""

import sqlite3

from .model import validate_recipe
from .storage import get_recipe, list_recipes, open_database, save_recipe


class Cancelled(Exception):
    """The user cancelled the current operation before saving."""


def read(prompt):
    value = input(prompt).strip()
    if value.casefold() == ":cancelar":
        raise Cancelled
    return value


def text(prompt, default=None):
    while True:
        value = read(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ")
        if value:
            return value
        if default is not None:
            return default
        print("Informe um texto não vazio.")


def number(prompt, maximum, *, integer=False, default=None):
    while True:
        raw = read(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ")
        if not raw and default is not None:
            return default
        try:
            value = int(raw) if integer else float(raw.replace(",", "."))
            if 0 < value <= maximum:
                return value
        except ValueError:
            pass
        kind = "um inteiro" if integer else "um número"
        print(f"Informe {kind} positivo de até {maximum}.")


def replace_list(label):
    while True:
        answer = read(f"Substituir {label}? [s/N]: ").casefold()
        if answer in ("s", "sim"):
            return True
        if answer in ("", "n", "não", "nao"):
            return False
        print("Responda s para sim ou n para não.")


def ingredients():
    print("Ingredientes: informe um por vez. Nome vazio encerra a lista.")
    items = []
    while True:
        name = read("Nome do ingrediente: ")
        if not name:
            if items:
                return items
            print("Informe pelo menos um ingrediente.")
            continue
        quantity = number("Quantidade (ponto ou vírgula decimal)", 1_000_000_000)
        unit = text("Unidade (ex.: g, ml, unidade)")
        items.append({"name": name, "quantity": quantity, "unit": unit})


def steps():
    print("Preparo: informe uma etapa por linha. Linha vazia encerra a lista.")
    items = []
    while True:
        step = read(f"Etapa {len(items) + 1}: ")
        if step:
            items.append(step)
        elif items:
            return items
        else:
            print("Informe pelo menos uma etapa.")


def show(recipe):
    print(f"\n{recipe['title']} — {recipe['servings']} porções")
    print("Ingredientes:")
    for item in recipe["ingredients"]:
        print(f"  - {item['quantity']} {item['unit']} de {item['name']}")
    print("Modo de preparo:")
    for index, step in enumerate(recipe["steps"], 1):
        print(f"  {index}. {step}")


def edit_form(current=None):
    print("\nDigite :cancelar em qualquer campo para voltar sem salvar.")
    if current is not None:
        show(current)
        print("Pressione Enter para manter os valores atuais.")
    previous = current or {}
    title = text("Título", previous.get("title"))
    servings = number("Porções", 10000, integer=True, default=previous.get("servings"))
    items = ingredients() if current is None or replace_list("os ingredientes") else current["ingredients"]
    preparation = steps() if current is None or replace_list("as etapas") else current["steps"]
    return validate_recipe({"title": title, "servings": servings,
                            "ingredients": items, "steps": preparation})


def run_menu(database):
    try:
        while True:
            try:
                print("\n=== Gerenciador de receitas ===\n"
                      "1. Cadastrar receita\n2. Listar receitas\n"
                      "3. Consultar receita\n4. Editar receita\n0. Sair")
                option = read("Escolha uma opção: ")
                if option == "0":
                    return 0
                if option == "2":
                    with open_database(database) as connection:
                        rows = list_recipes(connection)
                    for recipe_id, recipe in rows:
                        print(f"{recipe_id}: {recipe['title']} ({recipe['servings']} porções)")
                    if not rows:
                        print("Nenhuma receita cadastrada.")
                elif option in ("1", "3", "4"):
                    recipe_id, current = None, None
                    if option != "1":
                        recipe_id = number("ID da receita", 2**63 - 1, integer=True)
                        with open_database(database) as connection:
                            current = get_recipe(connection, recipe_id)
                    if option == "3":
                        show(current)
                        continue
                    # Keep user input outside the transaction; save only a complete form.
                    recipe = edit_form(current)
                    with open_database(database) as connection:
                        recipe_id = save_recipe(connection, recipe, recipe_id)
                    print(f"Receita {recipe_id} salva.")
                else:
                    print("Opção inválida. Escolha 0, 1, 2, 3 ou 4.")
            except Cancelled:
                print("Operação cancelada. Nenhuma alteração salva.")
            except (OSError, ValueError, sqlite3.Error) as error:
                print(f"Erro: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nMenu encerrado. Os dados já salvos foram preservados.")
        return 0
