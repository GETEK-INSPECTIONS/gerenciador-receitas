"""Photo decoding and storage checks use generated images and temporary data."""

import base64
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from recipes.photos import prepare_photo, store_photo
from recipes.storage import delete_recipe, get_recipe, open_database, save_recipe


def photo_payload(color="red", size=(12, 8), image_format="PNG", **metadata):
    output = BytesIO()
    with Image.new("RGB", size, color) as image:
        image.save(output, image_format)
    mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp"}[image_format]
    return {"data_url": "data:image/" + mime + ";base64," +
            base64.b64encode(output.getvalue()).decode("ascii"), **metadata}


class PhotoTests(unittest.TestCase):
    def test_accepts_raster_formats_and_outputs_jpeg(self):
        for image_format in ("JPEG", "PNG", "WEBP"):
            with self.subTest(image_format=image_format):
                result = prepare_photo(photo_payload(image_format=image_format))
                with Image.open(BytesIO(result["data"])) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, (12, 8))
                    self.assertEqual(image.mode, "RGB")

    def test_orientation_resize_and_metadata_removal(self):
        output = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "Private camera owner"
        with Image.new("RGB", (2400, 1200), "green") as image:
            image.save(output, "JPEG", exif=exif)
        payload = {"data_url": "data:image/jpeg;base64," +
                   base64.b64encode(output.getvalue()).decode("ascii")}
        with Image.open(BytesIO(prepare_photo(payload)["data"])) as image:
            self.assertEqual(image.size, (800, 1600))
            self.assertEqual(dict(image.getexif()), {})

    def test_rejects_corrupt_disguised_or_oversized_files(self):
        invalid = [
            {}, "bad", {"data_url": "data:image/svg+xml;base64,PHN2Zz4="},
            {"data_url": "data:image/png;base64,not valid base64"},
            {"data_url": "data:image/png;base64," + base64.b64encode(b"not an image").decode()},
            {**photo_payload(), "data_url": photo_payload()["data_url"].replace("image/png", "image/jpeg")},
            photo_payload(source_url="javascript:alert(1)"),
            photo_payload(credit=17),
        ]
        for payload in invalid:
            with self.subTest(payload=str(payload)[:80]), self.assertRaises(ValueError):
                prepare_photo(payload)
        with patch("recipes.photos.MAX_PHOTO_BYTES", 16), self.assertRaises(ValueError):
            prepare_photo(photo_payload())
        with patch("recipes.photos.MAX_PHOTO_PIXELS", 32), self.assertRaises(ValueError):
            prepare_photo(photo_payload())

    def test_photo_survives_recipe_edits_and_cascades_on_delete(self):
        recipe = {"title": "Soup", "servings": 2, "ingredients": [
            {"name": "Water", "quantity": 1, "unit": "l"}], "steps": ["Cook."]}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "recipes.db"
            with open_database(path) as connection:
                recipe_id = save_recipe(connection, recipe)
                store_photo(connection, recipe_id, prepare_photo(photo_payload(
                    credit="Test photographer", source_url="https://example.com/photo")))
            with open_database(path) as connection:
                save_recipe(connection, {**recipe, "title": "New soup"}, recipe_id)
                self.assertEqual(get_recipe(connection, recipe_id)["title"], "New soup")
                self.assertEqual(connection.execute("SELECT credit FROM recipe_photos").fetchone()[0],
                                 "Test photographer")
                delete_recipe(connection, recipe_id)
                self.assertEqual(connection.execute("SELECT count(*) FROM recipe_photos").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
