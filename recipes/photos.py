"""Validate uploads and keep normalized photos in the recipe database."""

import base64
import binascii
from io import BytesIO
import re
from urllib.parse import urlsplit

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_PHOTO_PIXELS = 40_000_000
MAX_PHOTO_EDGE = 1600


def prepare_photo(payload):
    """Decode real raster images; remove embedded metadata before storage."""
    if not isinstance(payload, dict) or set(payload) - {"data_url", "credit", "source_url"}:
        raise ValueError("A photo needs an image file and optional credit and source URL.")
    data_url = payload.get("data_url")
    if not isinstance(data_url, str):
        raise ValueError("Choose a JPEG, PNG or WebP photo.")
    header, separator, encoded = data_url.partition(",")
    match = re.fullmatch(r"data:image/(jpeg|png|webp);base64", header)
    if not separator or not match:
        raise ValueError("Choose a JPEG, PNG or WebP photo.")
    if len(encoded) > 4 * ((MAX_PHOTO_BYTES + 2) // 3):
        raise ValueError("Choose a photo no larger than 8 MB.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("The photo could not be read. Choose another image.") from None
    if not raw or len(raw) > MAX_PHOTO_BYTES:
        raise ValueError("Choose a photo no larger than 8 MB.")
    credit = payload.get("credit", "")
    source_url = payload.get("source_url", "")
    if not isinstance(credit, str) or len(credit) > 500:
        raise ValueError("Photo credit must be text of at most 500 characters.")
    if not isinstance(source_url, str) or len(source_url) > 2048:
        raise ValueError("Photo source URL must be text of at most 2048 characters.")
    source_url = source_url.strip()
    if source_url:
        parsed = urlsplit(source_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or any(char.isspace() for char in source_url)):
            raise ValueError("Photo source must be a valid HTTPS URL.")
    image_format = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[match[1]]
    try:
        with Image.open(BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as original:
            if original.format != image_format:
                raise ValueError("The photo contents do not match its file type.")
            if original.width * original.height > MAX_PHOTO_PIXELS:
                raise ValueError("Choose a photo with no more than 40 megapixels.")
            original.load()
            oriented = ImageOps.exif_transpose(original)
            oriented.thumbnail((MAX_PHOTO_EDGE, MAX_PHOTO_EDGE), Image.Resampling.LANCZOS)
            # A fresh RGB canvas drops EXIF, GPS, comments and other embedded metadata.
            rgb = Image.new("RGB", oriented.size, "white")
            rgba = oriented.convert("RGBA")
            rgb.paste(rgba, mask=rgba.getchannel("A"))
            output = BytesIO()
            rgb.save(output, "JPEG", quality=88, optimize=True)
            return {"data": output.getvalue(), "credit": credit.strip(), "source_url": source_url}
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("The photo could not be decoded. Choose another JPEG, PNG or WebP.") from None


def store_photo(connection, recipe_id, photo):
    """Store a prepared photo, or remove it with None, within the caller's transaction."""
    if photo is None:
        connection.execute("DELETE FROM recipe_photos WHERE recipe_id = ?", (recipe_id,))
    else:
        connection.execute(
            "INSERT INTO recipe_photos (recipe_id, data, credit, source_url) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(recipe_id) DO UPDATE SET data=excluded.data, "
            "credit=excluded.credit, source_url=excluded.source_url",
            (recipe_id, photo["data"], photo["credit"], photo["source_url"]),
        )


def photo_metadata(connection):
    return {recipe_id: {"photo_url": f"/api/recipes/{recipe_id}/photo",
                        "photo_credit": credit, "photo_source_url": source_url}
            for recipe_id, credit, source_url in connection.execute(
                "SELECT recipe_id, credit, source_url FROM recipe_photos")}
