import io
import json
import tempfile
import unittest
from pathlib import Path
from src.guard import run, УСПЕХ, НАРУШЕНИЕ_ПОЛИТИКИ, ОШИБКА_ИСХОДНИКА


class ТестыGuardCli(unittest.TestCase):
    def исходник(self, текст):
        файл = tempfile.NamedTemporaryFile("w", suffix=".яд", delete=False, encoding="utf-8")
        файл.write(текст); файл.close(); return файл.name

    def test_json_нарушение_и_exit_code(self):
        путь = self.исходник("функ старт() требует [ДоступСети] { вернуть сеть.отправить(пользователь.данные()) }")
        out, err = io.StringIO(), io.StringIO()
        код = run(["scan", путь, "--format", "json"], out, err)
        self.assertEqual(НАРУШЕНИЕ_ПОЛИТИКИ, код)
        self.assertEqual("ЯДРО-Э2301", json.loads(err.getvalue())["code"])

    def test_sarif_21(self):
        путь = self.исходник("функ старт() требует [ДоступСети] { вернуть сеть.отправить(пользователь.данные()) }")
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(НАРУШЕНИЕ_ПОЛИТИКИ, run(["scan", путь, "--format", "sarif"], out, err))
        self.assertEqual("2.1.0", json.loads(err.getvalue())["version"])

    def test_безопасная_программа_zero(self):
        self.assertEqual(УСПЕХ, run(["scan", self.исходник("функ старт() { вернуть 0 }")], io.StringIO(), io.StringIO()))

    def test_неверная_политика(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as файл:
            файл.write('{"version":"9"}'); путь = файл.name
        self.assertEqual(ОШИБКА_ИСХОДНИКА, run(["policy", "check", путь], io.StringIO(), io.StringIO()))

    def test_кастомная_политика(self):
        исходник = self.исходник("функ старт() требует [ВыполнениеИнструмента] { вернуть агент.выполнить(crm.клиент()) }")
        policy = Path(tempfile.mkstemp(suffix=".json")[1])
        policy.write_text(json.dumps({"version":"1.0", "sources":{"crm.клиент":"ПДн"},
                                      "sinks":{"агент.выполнить":"ВыполнениеИнструмента"}}, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(НАРУШЕНИЕ_ПОЛИТИКИ,
                         run(["scan", исходник, "--policy", str(policy)], io.StringIO(), io.StringIO()))


if __name__ == "__main__": unittest.main()
