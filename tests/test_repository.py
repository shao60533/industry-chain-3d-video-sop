"""Public documentation, template, and installable skill contract checks."""

import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evidence
import runtime
import setup


class RepositoryTests(unittest.TestCase):
    def documents(self) -> list[Path]:
        return (list(runtime.ROOT.glob("*.md")) + list((runtime.ROOT / "docs").glob("*.md")) +
                list((runtime.ROOT / "templates").rglob("*.md")) + list((runtime.ROOT / "assets").glob("*.md")))

    def test_relative_documentation_and_image_links(self) -> None:
        for document in self.documents():
            text = document.read_text(encoding="utf-8")
            links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text) + re.findall(r'<img[^>]+src="([^"]+)"', text)
            for link in links:
                if link.startswith(("https:", "http:", "mailto:", "file:")):
                    continue
                target, _, anchor = unquote(link).partition("#")
                path = (document.parent / target).resolve() if target else document
                self.assertTrue(path.exists(), f"Broken link: {document.name} -> {link}")
                if anchor and path.suffix == ".md":
                    headings = re.findall(r"^#+\s+(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
                    slugs = [re.sub(r"[^\w\-\u4e00-\u9fff ]", "", h.lower()).replace(" ", "-") for h in headings]
                    self.assertIn(anchor, slugs, f"Broken anchor: {document.name} -> {link}")

    def test_public_json_has_no_duplicate_keys_and_templates_remain_pending(self) -> None:
        files = list((runtime.ROOT / "templates").rglob("*.json")) + list((runtime.ROOT / "profiles").glob("*.json"))
        files += list((runtime.ROOT / "assets").glob("*.json"))
        for path in files:
            data = evidence.load_json(path)
            if path.name in ("step-evidence.template.json", "step-approval.template.json", "recovery-evidence.template.json"):
                self.assertEqual(data["status"], "pending")
            if path.name == "acceptance.template.json":
                self.assertEqual(set(data["checks"]), set(evidence.CHECKS))
                self.assertTrue(all(x["status"] == "pending" and x["report"] is None for x in data["checks"].values()))
        job = evidence.load_json(runtime.ROOT / "templates/next-episode/job.template.json")
        self.assertIsNone(job["content_kind"])
        self.assertIsNone(job["visual_style"])
        self.assertIsNone(job["workflow"])
        self.assertEqual(job["mode"], "produce_only")
        self.assertIsNone(job["publication_authorization"])

    def test_installable_skill_frontmatter_and_payload(self) -> None:
        text = (runtime.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---\n", 2)[1]
        name = re.search(r"^name: (.+)$", frontmatter, re.MULTILINE)
        description = re.search(r"^description: (.+)$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(name)
        self.assertIsNotNone(description)
        self.assertEqual(name.group(1), runtime.SKILL_NAME)
        self.assertLessEqual(len(description.group(1)), 1024)
        self.assertIn("scripts", setup.PAYLOAD)
        self.assertIn("tests", setup.PAYLOAD)


if __name__ == "__main__":
    unittest.main()
