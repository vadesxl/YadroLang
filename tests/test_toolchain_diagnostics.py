import types
import unittest
from unittest.mock import patch

from src import main


class ToolchainDiagnosticPrivacyTests(unittest.TestCase):
    def test_windows_clang_failure_does_not_echo_stderr(self):
        secret = "SECRET_TOKEN_FROM_TOOLCHAIN_STDERR"
        failure = types.SimpleNamespace(returncode=1, stdout="", stderr=secret * 5000)
        with patch.object(main.shutil, "which", return_value="clang"), patch.object(
            main, "_запустить_tool", return_value=failure
        ):
            with self.assertRaises(RuntimeError) as caught:
                main._создать_windows_coff(object(), "ignored.obj", "x86_64-pc-windows-msvc")
        message = str(caught.exception)
        self.assertNotIn(secret, message)
        self.assertLessEqual(len(message), 160)
        self.assertIn("кодом 1", message)

    def test_timeout_diagnostic_uses_tool_basename_not_full_command(self):
        error = main.subprocess.TimeoutExpired(
            ["/private/secret/path/clang", "--token=SECRET_ARGUMENT"], 30
        )
        with patch.object(main.subprocess, "run", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                main._запустить_tool(error.cmd, "tool stage")
        message = str(caught.exception)
        self.assertIn("clang", message)
        self.assertNotIn("SECRET_ARGUMENT", message)
        self.assertNotIn("/private/secret/path", message)


if __name__ == "__main__":
    unittest.main()
