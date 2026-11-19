"""Loopback-only browser interface, sharing the terminal app's SQLite storage."""

from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .calculations import format_measure, scale_ingredients, shopping_list
from .model import validate_recipe
from .planning import add_meal, list_meals, remove_meal, week_start
from .photos import photo_metadata, prepare_photo, store_photo
from .storage import delete_recipe, get_recipe, list_recipes, open_database, save_recipe


STATIC = Path(__file__).with_name("static")
DEFAULT_DATABASE = Path.home() / ".gerenciador-receitas" / "recipes.db"
ASSETS = {"/": ("index.html", "text/html"),
          "/app.js": ("app.js", "text/javascript"),
          "/styles.css": ("styles.css", "text/css")}


def measures(items):
    return [{"name": item["name"], "unit": item["unit"],
             "amount": format_measure(item["quantity"], item["unit"])}
            for item in items]


def save_web_recipe(connection, data, recipe_id=None):
    recipe = validate_recipe({key: value for key, value in data.items() if key != "photo"})
    photo = prepare_photo(data["photo"]) if data.get("photo") is not None else None
    recipe_id = save_recipe(connection, recipe, recipe_id)
    if "photo" in data:
        store_photo(connection, recipe_id, photo)
    return recipe_id


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, payload, content_type="application/json"):
        if content_type == "application/json":
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        charset = "; charset=utf-8" if content_type.startswith("text/") or content_type == "application/json" else ""
        self.send_header("Content-Type", content_type + charset)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data:; style-src 'self'; "
                         "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Send application/json.")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 12 * 1024 * 1024:
            raise ValueError("Request body must be between 1 byte and 12 MB.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object.")
        return data

    def dispatch(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        if (self.headers.get("Host") not in hosts
                or (origin and origin not in {f"http://{host}" for host in hosts})
                or (self.command != "GET" and self.headers.get("X-Recipe-Manager") != "1")):
            self.send(403, {"error": "Only requests from this local application are allowed."})
            return
        url = urlsplit(self.path)
        path = url.path
        query = parse_qs(url.query)
        if self.command == "GET" and path in ASSETS:
            filename, content_type = ASSETS[path]
            self.send(200, (STATIC / filename).read_bytes(), content_type)
            return
        data = self.read_json() if self.command in ("POST", "PUT") else {}
        status = 200
        with open_database(self.server.database) as connection:
            if (match := re.fullmatch(r"/api/recipes/([1-9][0-9]{0,17})/photo", path)) and self.command == "GET":
                row = connection.execute("SELECT data FROM recipe_photos WHERE recipe_id = ?",
                                         (int(match[1]),)).fetchone()
                if row is None:
                    self.send(404, {"error": "No photo is saved for this recipe."})
                else:
                    self.send(200, row[0], "image/jpeg")
                return
            if path == "/api/info" and self.command == "GET":
                result = {"application": "recipe-manager", "database": str(self.server.database)}
            elif path == "/api/recipes" and self.command == "GET":
                rows = list_recipes(connection, name=query.get("name", [None])[0],
                                    category=query.get("category", [None])[0])
                photos = photo_metadata(connection)
                result = [{"id": recipe_id, **recipe, **photos.get(recipe_id, {})}
                          for recipe_id, recipe in rows]
            elif path == "/api/recipes" and self.command == "POST":
                result = {"id": save_web_recipe(connection, data)}
                status = 201
            elif match := re.fullmatch(r"/api/recipes/([1-9][0-9]{0,17})(/scale)?", path):
                recipe_id = int(match[1])
                if match[2] and self.command == "GET":
                    recipe = get_recipe(connection, recipe_id)
                    servings = int(query.get("servings", [recipe["servings"]])[0])
                    result = measures(scale_ingredients(recipe, servings))
                elif not match[2] and self.command == "PUT":
                    result = {"id": save_web_recipe(connection, data, recipe_id)}
                elif not match[2] and self.command == "DELETE":
                    delete_recipe(connection, recipe_id)
                    result = {"deleted": recipe_id}
                else:
                    self.send(404, {"error": "Route not found."})
                    return
            elif path == "/api/meals" and self.command == "GET":
                week = week_start(query.get("week", [date.today().isoformat()])[0])
                result = {"week": week.isoformat(), "entries": list_meals(connection, week)}
            elif path == "/api/meals" and self.command == "POST":
                result = {"id": add_meal(connection, data["day"], data["meal"],
                                         data["recipe_id"], data["servings"])}
                status = 201
            elif (match := re.fullmatch(r"/api/meals/([1-9][0-9]{0,17})", path)) and self.command == "DELETE":
                remove_meal(connection, int(match[1]), query.get("week", [""])[0])
                result = {"deleted": int(match[1])}
            elif path == "/api/shopping" and self.command == "POST":
                if "week" in data:
                    selections = [(entry["recipe"], entry["servings"])
                                  for entry in list_meals(connection, data["week"])]
                else:
                    entries = data["selections"]
                    if not isinstance(entries, list) or len(entries) > 1000:
                        raise ValueError("Provide at most 1000 recipe selections.")
                    selections = []
                    for entry in entries:
                        if not isinstance(entry, dict) or type(entry.get("recipe_id")) is not int:
                            raise ValueError("Each selection needs a recipe ID and servings.")
                        selections.append((get_recipe(connection, entry["recipe_id"]), entry["servings"]))
                result = measures(shopping_list(selections))
            else:
                self.send(404, {"error": "Route not found."})
                return
        self.send(status, result)

    def handle_request(self):
        self.connection.settimeout(10)
        try:
            self.dispatch()
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            message = f"Missing field: {error.args[0]}." if isinstance(error, KeyError) else str(error)
            self.send(400, {"error": message or "Invalid request."})
        except sqlite3.Error:
            self.send(503, {"error": "The database is unavailable. Please try again."})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except OSError:
            self.send(500, {"error": "The application could not read its local files."})

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_DELETE = handle_request


def create_server(database=DEFAULT_DATABASE, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.database = Path(database).expanduser().resolve()
    return server


def run_web(database=DEFAULT_DATABASE, port=8765, open_browser=True):
    with create_server(database, port) as server:
        url = f"http://127.0.0.1:{server.server_port}"
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0
