import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from uploads import build_qr_payload, make_qr_png, save_uploaded_image


class UploadedBytes:
    def __init__(self, payload):
        self.payload = payload

    def getvalue(self):
        return self.payload


class UploadTests(unittest.TestCase):
    def _png(self):
        output = io.BytesIO()
        Image.new("RGB", (8, 8), color="crimson").save(output, format="PNG")
        return output.getvalue()

    def test_safe_upload_accepts_image_and_uses_generated_filename(self):
        with TemporaryDirectory() as directory:
            saved = Path(save_uploaded_image(UploadedBytes(self._png()), directory))
            self.assertEqual(saved.parent, Path(directory).resolve())
            self.assertTrue(saved.is_file())
            self.assertEqual(saved.suffix, ".jpg")

    def test_upload_rejects_non_image_content(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_uploaded_image(UploadedBytes(b"not an image"), directory)

    def test_qr_requires_trusted_https_url_and_has_no_personal_fields(self):
        with self.assertRaises(ValueError):
            build_qr_payload("http://example.test", "random-token")
        payload = build_qr_payload(
            "https://campus.example.edu/lost-found",
            "opaque-random-token",
        )
        self.assertEqual(
            payload,
            "https://campus.example.edu/lost-found/?qr=opaque-random-token",
        )
        for forbidden in ("roll", "email", "serial", "name"):
            self.assertNotIn(forbidden, payload.casefold())

    def test_qr_image_is_png(self):
        data = make_qr_png("https://localhost/?qr=opaque")
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
