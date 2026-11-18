"""Shared terminal input and cancellation helpers."""

class Cancelled(Exception):
    """The user cancelled the current operation before saving."""


def read(prompt):
    value = input(prompt).strip()
    if value.casefold() == ":cancel":
        raise Cancelled
    return value


def text(prompt, default=None):
    while True:
        value = read(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ")
        if value:
            return value
        if default is not None:
            return default
        print("Enter a non-empty value.")


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
        kind = "an integer" if integer else "a number"
        print(f"Enter {kind} greater than zero and no greater than {maximum}.")


def replace_list(label):
    while True:
        answer = read(f"Replace {label}? [y/N]: ").casefold()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Enter y for yes or n for no.")
