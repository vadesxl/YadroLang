import io
import json
import tempfile
import unittest

from src.guard import run, ОШИБКА_ИСХОДНИКА


class CheckedArithmeticGuardCliTests(unittest.TestCase):
    def source(self, text):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".яд", delete=False, encoding="utf-8"
        )
        handle.write(text)
        handle.close()
        return handle.name

    def test_a1002_is_source_error_without_traceback_or_source_echo(self):
        secret = "SENSITIVE_PAYLOAD_MUST_NOT_ECHO"
        expression = "9223372036854775807" + " + 0" * 257 + " + 1"
        path = self.source(f"# {secret}\nфунк старт() {{ вернуть {expression} }}")
        stdout, stderr = io.StringIO(), io.StringIO()
        result = run(
            ["compile", path, "--checked-arithmetic", "--ir", "--format", "json"],
            stdout,
            stderr,
        )
        self.assertEqual(ОШИБКА_ИСХОДНИКА, result)
        payload = json.loads(stderr.getvalue())
        self.assertEqual("ЯДРО-А1002", payload["code"])
        self.assertEqual(2, payload["line"])
        self.assertNotIn(secret, stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertEqual("", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
