import json,subprocess,sys,tempfile,unittest
class ТестыCheckedArithmeticCli(unittest.TestCase):
 def source(self,text):
  f=tempfile.NamedTemporaryFile("w",suffix=".яд",delete=False,encoding="utf-8");f.write(text);f.close();return f.name
 def cli(self,*args):return subprocess.run([sys.executable,"-m","src.guard_cli",*args],capture_output=True,text=True,timeout=30)
 def test_compile_flag_changes_ir(self):
  path=self.source("функ calc(x) { вернуть x + 1 } функ старт() { вернуть calc(1) }")
  default=self.cli("compile",path,"--ir");checked=self.cli("compile",path,"--ir","--checked-arithmetic")
  self.assertEqual(0,default.returncode,default.stderr);self.assertEqual(0,checked.returncode,checked.stderr);self.assertNotIn("sadd.with.overflow",default.stdout);self.assertIn("sadd.with.overflow",checked.stdout)
 def test_flag_rejected_outside_compile(self):
  path=self.source("функ старт() { вернуть 0 }")
  for command in ("scan","audit"):
   with self.subTest(command=command):self.assertEqual(2,self.cli(command,path,"--checked-arithmetic").returncode)
 def test_diagnostic_code_and_line(self):
  path=self.source("функ старт() { вернуть 9223372036854775807 + 1 }");result=self.cli("compile",path,"--checked-arithmetic","--format","json","--ir")
  self.assertEqual(3,result.returncode);payload=json.loads(result.stderr);self.assertEqual("ЯДРО-А1001",payload["code"]);self.assertEqual(1,payload["line"])
if __name__=="__main__":unittest.main()
