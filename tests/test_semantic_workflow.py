import re,unittest
from pathlib import Path

WORKFLOW=Path(__file__).resolve().parents[1]/".github"/"workflows"/"semantic-parity.yml"
class SemanticWorkflowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.text=WORKFLOW.read_text(encoding="utf-8")
 def test_counterpart_pin_is_immutable_sha(self):
  match=re.search(r"COUNTERPART_PIN: ([0-9a-f]+)",self.text);self.assertIsNotNone(match);self.assertRegex(match.group(1),r"^[0-9a-f]{40}$")
 def test_python_is_explicitly_provisioned(self):
  self.assertIn("actions/setup-python@v6",self.text);self.assertIn('python-version: "3.11"',self.text);self.assertNotIn("shell: python",self.text)
 def test_credentials_and_permissions_are_read_only(self):
  self.assertEqual(2,self.text.count("persist-credentials: false"));self.assertIn("permissions:\n  contents: read",self.text);self.assertNotRegex(self.text,r"contents:\s*write")
 def test_push_and_pull_paths_match(self):
  pull=self.text.split("  pull_request:\n",1)[1].split("  push:\n",1)[0]
  push=self.text.split("  push:\n",1)[1].split("  schedule:\n",1)[0]
  pull_paths={line.strip()[2:] for line in pull.splitlines() if line.strip().startswith("- ")}
  push_paths={line.strip()[2:] for line in push.splitlines() if line.strip().startswith("- ")}
  self.assertEqual(pull_paths,push_paths)
 def test_snapshot_and_freshness_are_separate(self):
  self.assertIn("snapshot-parity:",self.text);self.assertIn("pin-freshness:",self.text);self.assertIn("git ls-remote",self.text);self.assertIn("::warning",self.text)
if __name__=="__main__":unittest.main()
