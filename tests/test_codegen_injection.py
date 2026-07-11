import importlib,unittest
from src import кодоген_verified as backend
class ТестыВнедренияСимволов(unittest.TestCase):
 def test_manglers_are_instance_local(self):
  первый=backend.Кодоген(symbol_mangler=lambda kind,name:f"first_{kind}_{name}")
  второй=backend.Кодоген(symbol_mangler=lambda kind,name:f"second_{kind}_{name}")
  self.assertEqual("first_fn_main",первый.symbol_mangler("fn","main"));self.assertEqual("second_fn_main",второй.symbol_mangler("fn","main"))
 def test_facade_import_does_not_mutate_backend_default(self):
  исходный=backend.символ;import src.кодоген as facade;importlib.reload(facade);self.assertIs(исходный,backend.символ);self.assertIs(исходный,backend.Кодоген().symbol_mangler)
if __name__=="__main__":unittest.main()
