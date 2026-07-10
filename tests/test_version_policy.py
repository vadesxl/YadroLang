import io,json,tempfile,unittest
from src.guard import VERSION,run
class ТестыВерсииПолитики(unittest.TestCase):
 def fixture(self,payload):
  f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8");json.dump(payload,f,ensure_ascii=False);f.close();return f.name
 def test_stable_version(self):
  out=io.StringIO();self.assertEqual(0,run(["--version"],out,io.StringIO()));self.assertEqual("2.1.0",out.getvalue().strip());self.assertEqual("2.1.0",VERSION)
 def test_unknown_policy_field(self):self.assertEqual(3,run(["policy","check",self.fixture({"version":"1.0","oops":1})],io.StringIO(),io.StringIO()))
 def test_builtin_collision(self):self.assertEqual(3,run(["policy","check",self.fixture({"version":"1.0","sources":{"сеть.отправить":"ПДн"}})],io.StringIO(),io.StringIO()))
if __name__=="__main__":unittest.main()
