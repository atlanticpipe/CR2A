from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src/ is importable when running tests directly.
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from orchestrator.mime_utils import infer_extension_from_content_type_or_magic, infer_mime_type


class MimeUtilsTest(unittest.TestCase):
    def setUp(self):
        # Prepare a scratch directory per test to avoid mutating fixtures in-place.
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_pdf_detects_when_renamed_bin(self):
        # Copy a known PDF to a .bin name so detection must rely on content, not suffix.
        source = Path("cr2a_export.pdf")
        dest = self.tmpdir / "contract.bin"
        shutil.copyfile(source, dest)

        mime = infer_mime_type(dest)
        ext = infer_extension_from_content_type_or_magic(dest)

        self.assertEqual(mime, "application/pdf")
        self.assertEqual(ext, ".pdf")

    def test_docx_detects_when_renamed_bin(self):
        # Copy a known DOCX to a .bin name and expect content-based detection.
        source = Path("templates/CR2A_Template.docx")
        dest = self.tmpdir / "template.bin"
        shutil.copyfile(source, dest)

        mime = infer_mime_type(dest)
        ext = infer_extension_from_content_type_or_magic(dest)

        self.assertIn(mime, {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        })
        self.assertEqual(ext, ".docx")

    def test_unsupported_payload_raises(self):
        # A file with no recognizable signature or extension should raise.
        dest = self.tmpdir / "unknown.bin"
        dest.write_bytes(b"not-a-valid-document")

        with self.assertRaises(ValueError):
            infer_extension_from_content_type_or_magic(dest)


if __name__ == "__main__":
    unittest.main()
