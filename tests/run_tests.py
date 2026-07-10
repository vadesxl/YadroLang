import sys
import unittest
class AnnotatingResult(unittest.TextTestResult):
 def addFailure(self,test,err):
  super().addFailure(test,err);message=self._exc_info_to_string(err,test).replace("%","%25").replace("\r","%0D").replace("\n","%0A");print(f"::error title={test.id()}::{message}")
 def addError(self,test,err):
  super().addError(test,err);message=self._exc_info_to_string(err,test).replace("%","%25").replace("\r","%0D").replace("\n","%0A");print(f"::error title={test.id()}::{message}")
suite=unittest.defaultTestLoader.discover("tests",pattern="test_*.py");result=unittest.TextTestRunner(verbosity=2,resultclass=AnnotatingResult).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
