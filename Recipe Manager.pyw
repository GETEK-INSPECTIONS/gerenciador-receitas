"""Double-click to open Recipe Manager without a terminal window on Windows."""

import json
from tkinter import Tk, messagebox
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

from recipes.web import DEFAULT_DATABASE, run_web


def main():
    try:
        try:
            with urlopen("http://127.0.0.1:8765/api/info", timeout=2) as response:
                info = json.load(response)
        except URLError:
            info = None
        if (info and info.get("application") == "recipe-manager"
                and info.get("database") == str(DEFAULT_DATABASE.resolve())):
            webbrowser.open("http://127.0.0.1:8765")
        else:
            run_web()
    except Exception as error:
        root = Tk()
        root.withdraw()
        messagebox.showerror("Recipe Manager", f"Could not start the application.\n\n{error}")
        root.destroy()


if __name__ == "__main__":
    main()
