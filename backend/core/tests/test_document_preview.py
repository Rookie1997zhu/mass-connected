import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from core.document_preview import (
    MAX_VISION_PAGES,
    chunk_text,
    inspect_pdf_text_layer,
    preview_mode_for_ext,
    render_pdf_pages_as_images,
)


def _make_text_pdf(path: Path, page_texts: list[str]) -> None:
    import fitz

    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def _make_blank_pdf(path: Path, pages: int = 1) -> None:
    import fitz

    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(path)
    doc.close()


class DocumentPreviewHelpersTest(SimpleTestCase):
    def test_preview_mode_for_ext(self):
        self.assertEqual(preview_mode_for_ext("pdf"), "direct")
        self.assertEqual(preview_mode_for_ext("xlsx"), "pdf_convert")
        self.assertEqual(preview_mode_for_ext("docx"), "pdf_convert")
        self.assertEqual(preview_mode_for_ext("png"), "image")
        self.assertEqual(preview_mode_for_ext("zip"), "none")

    def test_chunk_text_single(self):
        self.assertEqual(chunk_text("hello"), ["hello"])

    def test_chunk_text_splits_long_text(self):
        text = "a" * 7000
        chunks = chunk_text(text, chunk_size=6000)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)

    def test_inspect_pdf_text_layer_detects_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "text.pdf"
            _make_text_pdf(pdf_path, ["Hello manufacturing"])
            result = inspect_pdf_text_layer(str(pdf_path))
            self.assertTrue(result["has_text_layer"])
            self.assertEqual(result["page_count"], 1)
            self.assertIn("Hello", result["text"])

    def test_inspect_pdf_text_layer_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "blank.pdf"
            _make_blank_pdf(pdf_path, pages=2)
            result = inspect_pdf_text_layer(str(pdf_path))
            self.assertFalse(result["has_text_layer"])
            self.assertEqual(result["page_count"], 2)
            self.assertEqual(result["text"], "")

    def test_render_pdf_pages_respects_max_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "many.pdf"
            _make_blank_pdf(pdf_path, pages=7)
            result = render_pdf_pages_as_images(str(pdf_path), max_pages=MAX_VISION_PAGES)
            self.assertEqual(result["page_count"], 7)
            self.assertEqual(result["processed_pages"], MAX_VISION_PAGES)
            self.assertTrue(result["truncated"])
            self.assertEqual(len(result["images"]), MAX_VISION_PAGES)
            first = result["images"][0]
            self.assertEqual(first["mime_type"], "image/jpeg")
            self.assertTrue(first["data"].startswith(b"\xff\xd8"))


class TranslateProjectPdfRoutingTest(SimpleTestCase):
    @patch("apps.project.translation.translate_file_text", return_value="译文")
    def test_text_layer_uses_text_translate(self, mock_text_translate):
        from apps.project.translation import translate_project_pdf_file

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "text.pdf"
            _make_text_pdf(pdf_path, ["Contract terms"])
            result = translate_project_pdf_file(99, str(pdf_path), "zh")
            self.assertEqual(result["extraction_method"], "pdf_text")
            self.assertEqual(result["translated_text"], "译文")
            mock_text_translate.assert_called_once()

    @patch("apps.project.translation.translate_pdf_pages_with_vision")
    def test_no_text_layer_uses_vision(self, mock_vision):
        from apps.project.translation import translate_project_pdf_file

        mock_vision.return_value = {
            "translated_text": "vision result",
            "truncated": False,
            "extraction_method": "gemini_vision",
            "page_count": 1,
            "processed_pages": 1,
            "char_count": 13,
        }
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "blank.pdf"
            _make_blank_pdf(pdf_path, pages=1)
            result = translate_project_pdf_file(100, str(pdf_path), "zh")
            self.assertEqual(result["extraction_method"], "gemini_vision")
            mock_vision.assert_called_once()

    @patch("apps.project.translation.cache")
    @patch("apps.project.translation.render_pdf_pages_as_images")
    def test_vision_cache_hit_skips_gemini(self, mock_render, mock_cache):
        from apps.project.translation import translate_pdf_pages_with_vision

        cached = {
            "translated_text": "cached",
            "truncated": False,
            "extraction_method": "gemini_vision",
            "page_count": 1,
            "processed_pages": 1,
            "char_count": 6,
        }
        mock_cache.get.return_value = cached
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "blank.pdf"
            _make_blank_pdf(pdf_path, pages=1)
            result = translate_pdf_pages_with_vision(101, str(pdf_path), "en")
            self.assertEqual(result["translated_text"], "cached")
            mock_render.assert_not_called()
