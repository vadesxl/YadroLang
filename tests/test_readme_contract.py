import re,unittest
from pathlib import Path
from src.version import VERSION
ROOT=Path(__file__).resolve().parents[1]
class ReadmeContractTests(unittest.TestCase):
 def test_version_is_consistent(self):
  readme=(ROOT/"README.md").read_text(encoding="utf-8")
  project=(ROOT/"pyproject.toml").read_text(encoding="utf-8")
  match=re.search(r'^version = "([^"]+)"$',project,re.MULTILINE)
  self.assertIsNotNone(match)
  self.assertEqual(VERSION,match.group(1))
  self.assertIn(f"YadroLang (ЯДРО) {VERSION}",readme)
  self.assertIn(f"version-{VERSION}-blue",readme)
 def test_security_boundaries_are_explicit(self):
  readme=(ROOT/"README.md").read_text(encoding="utf-8")
  for statement in ("не заявляется как production-ready","не доказывает его полноту","не обеспечивает authenticity/provenance","defense in depth"):
   with self.subTest(statement=statement):self.assertIn(statement,readme)
 def test_documented_entrypoints_exist(self):
  for path in ("CLI.md","FEATURE_STATUS.md","ABI.md","PROOF_SEAL.md","PROOF_SEAL_IMPLEMENTATION.md","LICENSE"):
   with self.subTest(path=path):self.assertTrue((ROOT/path).is_file(),path)
if __name__=="__main__":unittest.main()
