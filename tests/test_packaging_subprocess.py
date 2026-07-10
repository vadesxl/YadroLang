import json,subprocess,sys,tempfile,unittest
from pathlib import Path
class ТестыPackagingSubprocess(unittest.TestCase):
 def cli(self,*args):return subprocess.run([sys.executable,"-m","src.guard_cli",*args],text=True,capture_output=True,check=False)
 def test_version(self):
  result=self.cli("--version");self.assertEqual(0,result.returncode);self.assertIn("2.1.0",result.stdout)
 def test_type_error_это_source_error(self):
  with tempfile.NamedTemporaryFile("w",suffix=".яд",delete=False,encoding="utf-8") as f:f.write("функ старт() { вернуть истина + 1 }");path=f.name
  result=self.cli("scan",path,"--format","json");self.assertEqual(3,result.returncode);self.assertIn("ЯДРО-Т",json.loads(result.stderr)["message"])
 def test_unknown_и_builtin_collision_fail_closed(self):
  for data in ({"version":"1.0","unknown":{}},{"version":"1.0","sources":{"пользователь.данные":"ПДн"}}):
   policy=Path(tempfile.mkstemp(suffix=".json")[1]);policy.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8");self.assertEqual(3,self.cli("policy","check",str(policy)).returncode)
if __name__=="__main__":unittest.main()
