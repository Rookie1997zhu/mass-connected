from django.test import SimpleTestCase

from core.document_preview import chunk_text, preview_mode_for_ext


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
