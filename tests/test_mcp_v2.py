import io,json,tempfile,unittest
from src.guard_cli import run
class ТестыMcpV2(unittest.TestCase):
 def manifest(self,data):
  f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8");json.dump(data,f,ensure_ascii=False);f.close();return f.name
 def test_неизвестные_поля_и_capabilities(self):
  for data in ({"version":"1.0","tools":[],"oops":1},{"version":"1.0","tools":[{"name":"x","capabilities":["Root"]}]}):self.assertEqual(3,run(["mcp","scan",self.manifest(data)],io.StringIO(),io.StringIO()))
 def test_цикл_fixpoint_и_deterministic(self):
  path=self.manifest({"version":"1.0","tools":[{"name":"b","capabilities":["ДоступСети"]},{"name":"a","labels":["ПДн"]}],"flows":[["a","b"],["b","a"]]});out=io.StringIO();self.assertEqual(2,run(["mcp","scan",path,"--format","json"],out,io.StringIO()));payload=json.loads(out.getvalue());self.assertEqual(["b"],[i["tool"] for i in payload["findings"]]);self.assertEqual(2,payload["summary"]["flows"])
 def test_quiet(self):
  path=self.manifest({"version":"1.0","tools":[],"flows":[]});out=io.StringIO();self.assertEqual(0,run(["mcp","scan",path,"--quiet"],out,io.StringIO()));self.assertEqual("",out.getvalue())
 def test_sarif_file_uri(self):
  path=self.manifest({"version":"1.0","tools":[],"flows":[]});out=io.StringIO();self.assertEqual(0,run(["mcp","scan",path,"--format","sarif"],out,io.StringIO()));self.assertEqual("2.1.0",json.loads(out.getvalue())["version"])
if __name__=="__main__":unittest.main()
