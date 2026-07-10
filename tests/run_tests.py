import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class AnnotatingResult(unittest.TextTestResult):
 def _annotation(self,test,err):
  message=self._exc_info_to_string(err,test).replace("%","%25").replace("\r","%0D").replace("\n","%0A");print(f"::error title={test.id()}::{message}")
 def addFailure(self,test,err):super().addFailure(test,err);self._annotation(test,err)
 def addError(self,test,err):super().addError(test,err);self._annotation(test,err)
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern="test_*.py");result=unittest.TextTestRunner(verbosity=2,resultclass=AnnotatingResult).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
