import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def load(name, filename):
    s = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
installer = load("skill_installer", "install_skill.py")
mcp = load("skill_mcp", "configure_mcp.py")

class PortableTests(unittest.TestCase):
    def test_standard_skill(self):
        p = ROOT / "skills/sci-literature/SKILL.md"
        txt = p.read_text(encoding="utf-8")
        self.assertTrue(txt.startswith("---\n"))
        self.assertIn("\nname: sci-literature\n", txt)
        self.assertTrue((p.parent / "scripts/sci_refs.py").exists())
    def test_agents(self):
        with tempfile.TemporaryDirectory() as x:
            p = Path(x)
            expected = {".agents/skills/sci-literature",
                        ".claude/skills/sci-literature",
                        ".codebuddy/skills/sci-literature",
                        ".gemini/skills/sci-literature",
                        ".config/opencode/skills/sci-literature"}
            self.assertEqual(set(z.relative_to(p).as_posix() for z in installer.targets("all", "user", p, p)), expected)
    def test_no_clobber(self):
        with tempfile.TemporaryDirectory() as x:
            t = Path(x) / "sci-literature"
            installer.install(installer.SOURCE, t)
            with self.assertRaises(FileExistsError):
                installer.install(installer.SOURCE, t)
            installer.install(installer.SOURCE, t, force=True)
            self.assertEqual(len(list(Path(x).glob("sci-literature.backup.*"))), 1)
    def test_workbuddy_merge(self):
        with tempfile.TemporaryDirectory() as x:
            t = Path(x) / "mcp.json"
            t.write_text('{"mcpServers":{"existing":{"command":"safe"}}}', encoding="utf-8")
            mcp.merge_workbuddy_mcp(t, apply=True)
            d = json.loads(t.read_text())
            self.assertEqual(d["mcpServers"]["existing"]["command"], "safe")
            self.assertEqual(d["mcpServers"]["paper-search"]["command"], "uvx")
            self.assertEqual(len(list(Path(x).glob("mcp.json.backup.*"))), 1)

if __name__ == "__main__":
    unittest.main()
