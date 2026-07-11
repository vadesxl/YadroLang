import subprocess,unittest
from unittest.mock import patch
from src import main
class ТестыОшибокToolchain(unittest.TestCase):
 def test_missing_clang_is_controlled(self):
  with patch("src.main.shutil.which",return_value=None):
   with self.assertRaisesRegex(RuntimeError,"clang LLVM toolchain"):
    main._создать_windows_coff(object(),"unused.obj","x86_64-pc-windows-msvc")
 def test_clang_timeout_is_controlled(self):
  expired=subprocess.TimeoutExpired(["clang","-c"],main.ТАЙМАУТ_TOOL)
  with patch("src.main.subprocess.run",side_effect=expired):
   with self.assertRaisesRegex(RuntimeError,"clang COFF emission завис"):
    main._запустить_tool(["clang","-c"],"clang COFF emission")
if __name__=="__main__":unittest.main()
