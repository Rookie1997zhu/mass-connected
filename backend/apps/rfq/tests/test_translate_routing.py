from django.test import SimpleTestCase
from unittest.mock import patch

from apps.project.translation import translate_file_by_path
from core.document_preview import preview_cache_dir, cleanup_preview_cache


class TranslateFileByPathRoutingTest(SimpleTestCase):
    @patch("apps.project.translation.translate_pdf_file")
    def test_pdf_routes_to_pdf_helper(self, mock_pdf):
        mock_pdf.return_value = {
            "translated_text": "ok",
            "source_text": "src",
            "truncated": False,
            "extraction_method": "pdf_text",
            "page_count": 1,
            "processed_pages": 1,
            "char_count": 2,
        }
        result = translate_file_by_path("rfq_att", 9, "/tmp/a.pdf", "pdf", "en")
        mock_pdf.assert_called_once_with("rfq_att", 9, "/tmp/a.pdf", "en")
        self.assertEqual(result["translated_text"], "ok")

    @patch("apps.project.translation.translate_file_text", return_value="done")
    @patch("apps.project.translation.extract_text_from_file")
    def test_docx_extracts_then_translates(self, mock_extract, mock_text):
        mock_extract.return_value = {
            "text": "hello",
            "truncated": False,
            "extraction_method": "docx_parser",
            "page_count": 0,
            "char_count": 5,
        }
        result = translate_file_by_path("quote_att", 3, "/tmp/a.docx", "docx", "zh")
        mock_extract.assert_called_once()
        mock_text.assert_called_once_with("quote_att", 3, "hello", "zh")
        self.assertEqual(result["source_text"], "hello")
        self.assertEqual(result["translated_text"], "done")


class PreviewCacheNamespaceTest(SimpleTestCase):
    def test_preview_cache_dir_uses_namespace(self):
        path = preview_cache_dir(42, cache_ns="rfq_att")
        self.assertIn("rfq_att", str(path))
        self.assertIn("42", str(path))
        cleanup_preview_cache(42, cache_ns="rfq_att")
