import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class Result(unittest.TextTestResult):
 def mark(self,test,err):
  msg=self._exc_info_to_string(err,test).replace("%","%25").replace("\r","%0D").replace("\n","%0A");print(f"::error title={test.id()}::{msg}")
 def addFailure(self,test,err):super().addFailure(test,err);self.mark(test,err)
 def addError(self,test,err):super().addError(test,err);self.mark(test,err)
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent));result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
