import shutil,subprocess,tempfile,unittest,os,io,contextlib
from pathlib import Path
from src.abi import external_symbol
from src.main import компилировать,собрать_нативно
class ТестыNativeAbi(unittest.TestCase):
 def test_c_compatible_collision_resistant(self):
  names=[external_symbol(x) for x in ("сеть.отправить","сеть_отправить","net.send")];self.assertEqual(3,len(set(names)))
  for name in names:self.assertRegex(name,r"^[A-Za-z_][A-Za-z0-9_]*$")
 def test_native_link_run(self):
  cc=next((shutil.which(x) for x in ("clang","cc","gcc") if shutil.which(x)),None)
  if not cc:self.skipTest("нет C linker")
  source='функ старт() требует [ДоступСети] { пусть x = пользователь.данные() пусть y = анонимизировать(x) вернуть сеть.отправить(y) }'
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);obj=d/"program.obj"
   with contextlib.redirect_stdout(io.StringIO()):собрать_нативно(компилировать(source),str(obj))
   c=d/"runtime.c";c.write_text("#include <stdint.h>\n"+f"int64_t {external_symbol('пользователь.данные')}(void){{return 41;}}\n"+f"int64_t {external_symbol('анонимизировать')}(int64_t x){{return x+1;}}\n"+f"int64_t {external_symbol('сеть.отправить')}(int64_t x){{return x;}}\n",encoding="utf-8");exe=d/("app.exe" if os.name=='nt' else "app");command=[cc,str(obj),str(c),"-o",str(exe)];command[1:1]=["-fuse-ld=lld"] if os.name=='nt' else [];link=subprocess.run(command,capture_output=True,text=True);self.assertEqual(0,link.returncode,f"command={command}\nstdout={link.stdout}\nstderr={link.stderr}");result=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual(0,result.returncode,f"stdout={result.stdout}\nstderr={result.stderr}");self.assertIn("42",result.stdout)
if __name__=="__main__":unittest.main()
