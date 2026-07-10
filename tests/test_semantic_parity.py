import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from tools.check_parity import configure_utf8

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"check_parity.py"
MANIFEST=ROOT/"spec"/"semantic_surface.json"

class ReconfigurableStream:
 def __init__(self):self.calls=[]
 def reconfigure(self,**kwargs):self.calls.append(kwargs)

class SemanticParityTests(unittest.TestCase):
 def setUp(self):
  self.base=json.loads(MANIFEST.read_text(encoding="utf-8"))
  self.other=copy.deepcopy(self.base);self.other["language"]="en";self.other["localized"]={key:f"en_{key}" for key in self.base["surface"]["keywords"]}
 def run_pair(self,left=None,right=None,right_raw=None):
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);a=tmp/"left.json";b=tmp/"right.json"
   a.write_text(json.dumps(self.base if left is None else left,ensure_ascii=False),encoding="utf-8")
   b.write_text(right_raw if right_raw is not None else json.dumps(self.other if right is None else right,ensure_ascii=False),encoding="utf-8")
   return subprocess.run([sys.executable,str(SCRIPT),str(a),str(b)],capture_output=True,encoding="utf-8",errors="strict")
 def assert_error(self,result,text):
  self.assertEqual(1,result.returncode,result.stdout+result.stderr);self.assertIn("parity error:",result.stderr);self.assertIn(text,result.stderr)
 def test_real_manifest_pair_passes(self):
  result=self.run_pair();self.assertEqual(0,result.returncode,result.stderr);self.assertEqual("semantic parity OK: ru <-> en",result.stdout.strip())
 def test_surface_drift_fails_deterministically_with_unicode(self):
  changed=copy.deepcopy(self.other);changed["surface"]["capabilities"].append("секрет")
  first=self.run_pair(right=changed);second=self.run_pair(right=changed)
  self.assert_error(first,"semantic surfaces differ");self.assertEqual(first.stderr,second.stderr);self.assertIn("секрет",first.stderr)
 def test_same_language_rejected(self):
  changed=copy.deepcopy(self.other);changed["language"]="ru";self.assert_error(self.run_pair(right=changed),"different localizations")
 def test_missing_top_level_key_rejected(self):
  changed=copy.deepcopy(self.other);del changed["localized"];self.assert_error(self.run_pair(right=changed),"expected top-level keys")
 def test_duplicate_keywords_rejected(self):
  changed=copy.deepcopy(self.other);changed["surface"]["keywords"].append("function");self.assert_error(self.run_pair(right=changed),"unique string list")
 def test_localized_coverage_rejected(self):
  changed=copy.deepcopy(self.other);del changed["localized"]["function"];self.assert_error(self.run_pair(right=changed),"localized keys")
 def test_malformed_json_is_controlled(self):self.assert_error(self.run_pair(right_raw="{"),"Expecting")
 def test_utf8_configuration_is_guarded(self):
  stream=ReconfigurableStream();self.assertIs(stream,configure_utf8(stream));self.assertEqual([{"encoding":"utf-8","errors":"backslashreplace"}],stream.calls);self.assertIsNotNone(configure_utf8(object()))

if __name__=="__main__":unittest.main()
