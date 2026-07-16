import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT_PATH = Path(__file__).with_name("reconcile_media.py")
_spec = importlib.util.spec_from_file_location("reconcile_media", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_module)

reconcile = _module.reconcile


def write_pattern_png(path: Path, size: tuple[int, int]) -> None:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 13 + y * 7) % 256, (x * 5) % 256, (y * 11) % 256)
    image.save(path)


class ReconcileMediaTests(unittest.TestCase):
    def _write_project(self, root: Path, include_illustration: bool = True) -> None:
        (root / "imgs" / "prompts").mkdir(parents=True)
        (root / "prompts").mkdir()
        (root / "prompts" / "cover.md").write_text("cover prompt", encoding="utf-8")
        (root / "imgs" / "prompts" / "01-flowchart-core-flow.md").write_text(
            "illustration prompt",
            encoding="utf-8",
        )
        (root / "imgs" / "outline.md").write_text(
            "## Illustration 1\n"
            "**Position**: 第一节后\n"
            "**Purpose**: 展示核心流程\n"
            "**Filename**: 01-flowchart-core-flow.png\n",
            encoding="utf-8",
        )
        (root / "公众号_文章.md").write_text(
            "# 标题\n\n![展示核心流程](imgs/01-flowchart-core-flow.png)\n",
            encoding="utf-8",
        )
        (root / "公众号_文章.html").write_text(
            '<p><img src="imgs/01-flowchart-core-flow.png"></p>',
            encoding="utf-8",
        )
        write_pattern_png(root / "公众号_封面.png", (900, 383))
        if include_illustration:
            write_pattern_png(root / "imgs" / "01-flowchart-core-flow.png", (1920, 1080))

    def test_matching_media_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_project(root)

            result = reconcile(root, require_cover=True, require_illustrations=True)

            self.assertTrue(result["passed"], result)
            self.assertEqual([], result["failures"])

    def test_missing_referenced_image_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_project(root, include_illustration=False)

            result = reconcile(root, require_cover=True, require_illustrations=True)

            self.assertFalse(result["passed"])
            self.assertTrue(any(item["code"] == "IMAGE_MISSING" for item in result["failures"]))

    def test_html_generation_may_precede_images_but_reconciliation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_project(root, include_illustration=False)

            self.assertTrue((root / "公众号_文章.html").exists())
            result = reconcile(root, require_cover=True, require_illustrations=True)

            self.assertFalse(result["passed"])

    def test_string_cover_does_not_crash_prompt_hash_verification(self) -> None:
        # Regression: phase6.generate.cover is documented as an object, but an
        # older/partial state.json may still carry a placeholder string
        # ("pending"). verify_prompt_hashes must skip the hash check gracefully
        # instead of raising AttributeError on .get().
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_project(root)
            (root / "state.json").write_text(
                json.dumps({
                    "phase6": {"generate": {"cover": "pending",
                                            "illustrations": {"status": "pending", "items": []}}},
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            result = reconcile(root, require_cover=True, require_illustrations=True,
                               verify_prompt_hash=True)

            self.assertTrue(result["passed"], result)
            self.assertEqual([], result["failures"])


if __name__ == "__main__":
    unittest.main()
