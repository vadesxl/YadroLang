import io
import tempfile
import unittest
from pathlib import Path
from src.guard import run, УСПЕХ, НАРУШЕНИЕ_ПОЛИТИКИ
from src import report_html


class ТестыHtmlОтчёта(unittest.TestCase):
    def setUp(self):
        self.папка = Path(tempfile.mkdtemp())

    def исходник(self, текст):
        путь = self.папка / "prog.яд"
        путь.write_text(текст, encoding="utf-8")
        return путь

    def test_нарушение_рисует_путь_утечки_и_exit_code(self):
        путь = self.исходник("функ старт() требует [ДоступСети] {\n  пусть х = пользователь.данные()\n  вернуть сеть.отправить(х)\n}")
        out = io.StringIO()
        self.assertEqual(НАРУШЕНИЕ_ПОЛИТИКИ, run(["scan", str(путь), "--format", "html"], out, io.StringIO()))
        отчёт = (self.папка / "prog.report.html").read_text(encoding="utf-8")
        self.assertIn("Обнаружена утечка", отчёт)
        self.assertIn("ЯДРО-Э2301", отчёт)
        self.assertIn("пользователь.данные()", отчёт)
        self.assertIn("сеть.отправить", отчёт)
        self.assertIn("Персональные данные", отчёт)   # человеческое имя метки
        self.assertIn("Карантин", отчёт)               # панель "как исправить"
        self.assertIn('class="hit"', отчёт)
        self.assertIn("отчёт:", out.getvalue())

    def test_чистая_программа_зелёный_вердикт_и_санитайз(self):
        путь = self.исходник("функ старт() { пусть х = платеж.карта() пусть у = зашифровать(х) вернуть у }")
        self.assertEqual(УСПЕХ, run(["scan", str(путь), "--format", "html"], io.StringIO(), io.StringIO()))
        отчёт = (self.папка / "prog.report.html").read_text(encoding="utf-8")
        self.assertIn("Утечек не найдено", отчёт)
        self.assertIn("зашифровать", отчёт)

    def test_явный_путь_отчёта(self):
        путь = self.исходник("функ старт() { вернуть 0 }")
        цель = self.папка / "custom.html"
        run(["audit", str(путь), "--format", "html", "--report", str(цель)], io.StringIO(), io.StringIO())
        self.assertTrue(цель.exists())

    def test_исходник_экранируется_и_нет_скриптов(self):
        вредный = "функ старт() { вернуть 0 }\n# <script>alert(1)</script> <img src=x onerror=alert(1)>"
        диагностика = {"message": "<script>x</script> строка 1", "code": "<b>", "line": 1}
        for html in (report_html.построить("<p>", вредный, диагностика, None, "<v>"),
                     report_html.построить("<p>", вредный, None, [], "<v>")):
            self.assertNotIn("<script", html.lower())
            self.assertNotIn("<img", html.lower())
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("default-src 'none'", html)


class ТестыТочкиВходаCli(unittest.TestCase):
    def test_python_m_src_guard_не_fail_open(self):
        import os, subprocess, sys
        корень = Path(__file__).resolve().parents[1]
        плохой = Path(tempfile.mkdtemp()) / "leak.яд"
        плохой.write_text("функ старт() требует [ДоступСети] { вернуть сеть.отправить(пользователь.данные()) }", encoding="utf-8")
        среда = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        версия = subprocess.run([sys.executable, "-m", "src.guard", "version"], cwd=корень, env=среда,
                                capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(0, версия.returncode)
        self.assertRegex(версия.stdout, r"\d+\.\d+\.\d+")
        скан = subprocess.run([sys.executable, "-m", "src.guard", "scan", str(плохой)], cwd=корень, env=среда,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(НАРУШЕНИЕ_ПОЛИТИКИ, скан.returncode)


if __name__ == "__main__":
    unittest.main()
