import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skill' / 'scripts'))
import sci_refs as s

WORK = {
    "DOI": "10.1234/demo",
    "title": ["Numerical investigation of tunnel lining deformation"],
    "container-title": ["Synthetic Engineering Journal"],
    "published": {"date-parts": [[2024, 5, 1]]},
    "type": "journal-article",
    "author": [{"given": "Alex", "family": "Example"}],
    "volume": "22",
    "issue": "4",
    "page": "101-118",
}


class SciRefsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'sections').mkdir()
        (self.root / 'literature').mkdir()
        self.tex = self.root / 'sections' / 'introduction.tex'
        self.bib = self.root / 'references.bib'
        self.key = 'example2024Numerical'
        self.bib.write_text(s.work_to_bib(WORK, self.key), encoding='utf-8')
        s.dump_json(self.root / 'literature/doi-ledger.json', {
            'schema': 1, 'records': {'10.1234/demo': {'key': self.key, 'status': 'metadata_verified'}}})
        self.sentence = 'The lining deforms under the additional ground load.'
        self.tex.write_text('% ' + self.sentence + '\n' + self.sentence + '\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, **overrides):
        proposal = {
            'file': 'sections/introduction.tex',
            'anchor': self.sentence,
            'keys': [self.key],
            'cite_command': 'cite',
            'placement': 'before_punctuation',
            'approved': True,
            'evidence': [{
                'key': self.key,
                'doi': '10.1234/demo',
                'basis': 'full_text',
                'locator': 'p. 3, Figure 2',
                'support': 'direct',
                'finding': 'The synthetic example directly addresses lining deformation.'
            }]
        }
        proposal.update(overrides)
        path = self.root / 'literature/plan.json'
        s.dump_json(path, {'proposals': [proposal]})
        return path

    def insert_args(self, apply):
        return ['insert', '--root', str(self.root), '--bib', 'references.bib', '--ledger', 'literature/doi-ledger.json',
                '--plan', 'literature/plan.json'] + (['--apply'] if apply else [])

    def run_cli(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return s.main(args)

    def test_normalize_doi(self):
        self.assertEqual(s.normalize_doi('https://doi.org/10.1234/DEMO'), '10.1234/demo')
        with self.assertRaises(ValueError):
            s.normalize_doi('not-a-doi')

    def test_bib_parse_preserves_nested_title(self):
        entries = s.bib_entries(self.bib)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['doi'], '10.1234/demo')
        self.assertEqual(entries[0]['key'], self.key)
        self.assertIn('Numerical investigation', entries[0]['fields']['title'])

    def test_mask_tex_comments(self):
        masked = s.mask_tex(self.tex.read_text())
        self.assertEqual(masked.count(self.sentence), 1)

    def test_insert_preview_does_not_write(self):
        self.plan()
        before = self.tex.read_bytes()
        self.assertEqual(self.run_cli(self.insert_args(False)), 0)
        self.assertEqual(before, self.tex.read_bytes())

    def test_insert_apply_creates_backup(self):
        self.plan()
        self.assertEqual(self.run_cli(self.insert_args(True)), 0)
        text = self.tex.read_text()
        self.assertIn('ground load \\cite{' + self.key + '}.', text)
        self.assertEqual(len(list(self.tex.parent.glob('introduction.tex.bak.*'))), 1)

    def test_unapproved_plan_blocks_changes(self):
        self.plan(approved=False)
        self.assertEqual(self.run_cli(self.insert_args(True)), 2)
        self.assertNotIn('\\cite{', self.tex.read_text())

    def test_unsupported_evidence_blocks_changes(self):
        evidence = [{"key": self.key, "basis": "metadata_only", "locator": "Crossref", "support": "direct", "finding": "Metadata is not substantive claim evidence."}]
        self.plan(evidence=evidence)
        self.assertEqual(self.run_cli(self.insert_args(True)), 2)

    def test_ambiguous_anchor_blocks_changes(self):
        self.plan()
        self.tex.write_text(self.sentence + '\n' + self.sentence + '\n', encoding='utf-8')
        self.assertEqual(self.run_cli(self.insert_args(True)), 2)

    def test_audit_missing_key(self):
        self.tex.write_text('Text \\cite{undefinedkey}.\n', encoding='utf-8')
        self.assertEqual(self.run_cli(['audit', '--root', str(self.root), '--bib', 'references.bib']), 1)

    def test_audit_duplicate_doi(self):
        with self.bib.open('a', encoding='utf-8') as f:
            f.write('\n@article{other2024, title={Other}, doi={https://doi.org/10.1234/DEMO}}\n')
        self.assertEqual(self.run_cli(['audit', '--root', str(self.root), '--bib', 'references.bib']), 1)

    def test_import_is_idempotent(self):
        with mock.patch.object(s, 'crossref_doi', return_value=WORK):
            self.assertEqual(self.run_cli(['import', '--doi', '10.1234/demo', '--bib', str(self.bib), '--ledger', str(self.root / 'literature/doi-ledger.json')]), 0)
        self.assertEqual(len(s.bib_entries(self.bib)), 1)

    def test_verify_flags_title_mismatch(self):
        self.bib.write_text('@article{example2024Numerical, title={Completely unrelated title}, year={2024}, doi={10.1234/demo}}', encoding='utf-8')
        with mock.patch.object(s, 'crossref_doi', return_value=WORK):
            self.assertEqual(self.run_cli(['verify', '--bib', str(self.bib), '--ledger', str(self.root / 'literature/doi-ledger.json')]), 1)

    def test_crlf_preserved_on_apply(self):
        self.plan()
        with self.tex.open('w', encoding='utf-8', newline='') as fh:
            fh.write('% comment\r\n' + self.sentence + '\r\n')
        self.assertEqual(self.run_cli(self.insert_args(True)), 0)
        data = self.tex.read_bytes()
        self.assertIn(b'\r\n', data)
        self.assertNotIn(b'\n', data.replace(b'\r\n', b''))


if __name__ == '__main__':
    unittest.main()
