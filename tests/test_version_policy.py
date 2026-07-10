import io,json,tempfile,unittest
from src.guard import VERSION,run
class ТестыВерсииПолитики(unittest.TestCase):
 def test_stable_version(self):
  out=io.StringIO();self.assertEqual(0,run(["--version"],out,io.StringIO()));self.assertEqual("2.1.0",out.getvalue().strip());self.assertEqual("2.1.0",VERSION)
 def test_unknown_policy_field(self):
  f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False);json.dump({"version":"1.0","oops":1},f);f.close();self.assertEqual(3,run(["policy","check",f.name],io.StringIO(),io.StringIO()))
 def test_builtin_collision(self):
  f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False);json.dump({"version":"1.0","sources":{"сеть.отправить":"ПДн"}},f,ensure_ascii=False);f.close();self.assertEqual(3,run(["policy","check",f.name],io.StringIO(),io.StringIO()))
if __name__=="__main__":unittest.main()
