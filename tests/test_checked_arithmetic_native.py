import contextlib,io,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from src.abi import external_symbol
from src.main import компилировать,собрать_нативно
TIMEOUT=30
class ТестыCheckedArithmeticNative(unittest.TestCase):
 def setUp(self):
  self.cc=next((shutil.which(x) for x in ("clang","cc","gcc") if shutil.which(x)),None)
  if not self.cc:self.fail("обязательный C compiler/linker не найден в PATH")
 def run_case(self,expression,value):
  source=f"функ старт() {{ пусть x = анонимизировать(пользователь.данные()) вернуть {expression} }}"
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);obj=folder/"program.obj"
   with contextlib.redirect_stdout(io.StringIO()):собрать_нативно(компилировать(source,арифметика="checked"),str(obj))
   if os.name=="nt":self.assertEqual(b"\x64\x86",obj.read_bytes()[:2],"ожидался AMD64 COFF magic")
   c=folder/"runtime.c";c.write_text("#include <stdint.h>\n"+f"int64_t {external_symbol('пользователь.данные')}(void){{return (int64_t)({value});}}\n"+f"int64_t {external_symbol('анонимизировать')}(int64_t x){{return x;}}\n",encoding="utf-8")
   exe=folder/("app.exe" if os.name=="nt" else "app");command=[self.cc,str(obj),str(c),"-o",str(exe)];command[1:1]=["-fuse-ld=lld"] if os.name=="nt" else []
   try:link=subprocess.run(command,capture_output=True,text=True,timeout=TIMEOUT)
   except subprocess.TimeoutExpired as error:self.fail(f"native link завис более {TIMEOUT}s: {error.cmd[0]}")
   self.assertEqual(0,link.returncode,f"command={command}\nstdout={link.stdout}\nstderr={link.stderr}")
   try:return subprocess.run([str(exe)],capture_output=True,timeout=TIMEOUT)
   except subprocess.TimeoutExpired as error:self.fail(f"native executable завис более {TIMEOUT}s: {error.cmd[0]}")
 def test_safe_boundary(self):
  result=self.run_case("x + 0","9223372036854775807");self.assertEqual(0,result.returncode);self.assertIn(b"9223372036854775807",result.stdout)
 def test_runtime_traps(self):
  cases=(("x + 1","9223372036854775807"),("x - 1","-9223372036854775807 - 1"),("x * 2","9223372036854775807"),("1 / x","0"),("x / -1","-9223372036854775807 - 1"))
  for expression,value in cases:
   with self.subTest(expression=expression):self.assertNotEqual(0,self.run_case(expression,value).returncode)
if __name__=="__main__":unittest.main()
