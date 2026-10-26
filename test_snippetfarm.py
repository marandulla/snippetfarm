"""snippetfarm —— 自检测试。

按用途管理提示词片段，支持按标签检索、组合与版本对照。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snippetfarm  # noqa: E402


class TestSnippetFarm(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.write("role.md", "role", ["role"], "1", "你是客服助手。")
        self.write("constraint.md", "constraint", ["constraint"], "2",
                   "不要编造信息。")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write(self, fn, name, tags, version, body):
        with open(os.path.join(self.tmpdir, fn), "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"name: {name}\n")
            f.write(f"tags: [{', '.join(tags)}]\n")
            f.write(f"version: {version}\n")
            f.write("---\n")
            f.write(body + "\n")

    def test_snippets_are_loaded(self):
        s = snippetfarm.load_snippets(self.tmpdir)
        self.assertEqual(len(s), 2)
        self.assertEqual(sorted(x["name"] for x in s), ["constraint", "role"])

    def test_search_by_keyword(self):
        s = snippetfarm.load_snippets(self.tmpdir)
        hits = snippetfarm.search(s, "客服")
        self.assertTrue(hits)

    def test_search_by_tag(self):
        s = snippetfarm.load_snippets(self.tmpdir)
        hits = snippetfarm.search(s, "", "constraint")
        self.assertEqual(len(hits), 1)

    def test_compose_joins_snippets(self):
        s = snippetfarm.load_snippets(self.tmpdir)
        text, missing = snippetfarm.compose(s, ["role", "constraint"])
        self.assertEqual(missing, [])
        self.assertIn("你是客服助手", text)
        self.assertIn("不要编造", text)

    def test_compose_reports_missing(self):
        s = snippetfarm.load_snippets(self.tmpdir)
        text, missing = snippetfarm.compose(s, ["nonexistent"])
        self.assertEqual(missing, ["nonexistent"])

    def test_version_diff_detected(self):
        self.write("role2.md", "role", ["role"], "2", "你是技术支持助手。")
        s = snippetfarm.load_snippets(self.tmpdir)
        diffs = snippetfarm.diff_versions(s)
        self.assertTrue(diffs)
        self.assertLess(diffs[0]["similarity"], 1.0)
