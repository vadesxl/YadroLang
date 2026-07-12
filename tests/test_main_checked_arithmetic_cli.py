import os
import subprocess
import sys
import tempfile
import unittest


class MainCheckedArithmeticCliTests(unittest.TestCase):
    def source(self, text):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".яд", delete=False, encoding="utf-8"
        )
        self.addCleanup(lambda: os.path.exists(handle.name) and os.unlink(handle.name))
        handle.write(text)
        handle.close()
        return handle.name

    def cli(self, *args):
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        return subprocess.run(
            [sys.executable, "-m", "src.main", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
            env=env,
        )

    def test_checked_flag_is_honored_in_direct_cli(self):
        path = self.source("функ calc(x) { вернуть x + 1 } функция старт() { вернуть calc(1) }".replace("функция", "функ"))
        result = self.cli(path, "--ir", "--checked-arithmetic")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("llvm.sadd.with.overflow.i64", result.stdout)

    def test_unknown_and_misspelled_flags_fail_closed(self):
        path = self.source("функ старт() { вернуть 0 }")
        for flag in ("--checked-arithmeti", "--fast-magic", "--unknown"):
            with self.subTest(flag=flag):
                result = self.cli(path, flag)
                self.assertEqual(2, result.returncode)
                self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
