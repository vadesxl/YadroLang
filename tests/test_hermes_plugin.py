import asyncio
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parents[1]
ПЛАГИН = КОРЕНЬ / "integrations" / "hermes" / "yadro-guard"


def _загрузить_api(папка_плагина):
    spec = importlib.util.spec_from_file_location("yg_plugin_api", папка_плагина / "dashboard" / "plugin_api.py")
    мод = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(мод)
    return мод


class ТестыПлагинаHermes(unittest.TestCase):
    def setUp(self):
        self.папка = Path(tempfile.mkdtemp())
        (self.папка / "dashboard").mkdir()
        (self.папка / "dashboard" / "plugin_api.py").write_text(
            (ПЛАГИН / "dashboard" / "plugin_api.py").read_text(encoding="utf-8"), encoding="utf-8")
        (self.папка / "config.json").write_text(
            json.dumps({"engine_home": str(КОРЕНЬ), "python": sys.executable}), encoding="utf-8")
        self.api = _загрузить_api(self.папка)

    def тело(self, код, title=""):
        return self.api.CodeBody(code=код, title=title)

    def test_манифест_как_у_hermes(self):
        м = json.loads((ПЛАГИН / "dashboard" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("yadro-guard", м["name"])
        for ключ in ("entry", "css", "api", "tab"):
            self.assertIn(ключ, м)
        for файл in (м["entry"], м["css"], м["api"]):
            self.assertTrue((ПЛАГИН / "dashboard" / файл).exists(), файл)

    def test_анализ_вставленного_кода_и_история_без_кода(self):
        код = "fn main() requires [NetworkAccess] {\n  let key = env.secret()\n  return net.send(key)\n}"
        р = asyncio.run(self.api.analyze(self.тело(код, "payment agent")))
        self.assertEqual("leak", р["status"])
        self.assertEqual("Credentials & keys", р["labels"][0]["label"])
        self.assertTrue(р["autofix"]["verified"])
        история = asyncio.run(self.api.history())["items"]
        self.assertEqual("payment agent", история[0]["title"])
        self.assertNotIn("env.secret", json.dumps(история))   # сам код в историю не пишется

    def test_пустой_код_и_битый_секрет_отклоняются(self):
        self.assertEqual("error", asyncio.run(self.api.analyze(self.тело("   ")))["status"])
        плохой = self.api.SecretBody(secret="x", label="Passwords")
        self.assertEqual("error", asyncio.run(self.api.vault_put(плохой))["status"])

    def test_без_настройки_честная_ошибка(self):
        (self.папка / "config.json").unlink()
        self.assertEqual("error", asyncio.run(self.api.analyze(self.тело("fn main() { return 0 }")))["status"])
        self.assertFalse(asyncio.run(self.api.health())["configured"])

    def test_фронтенд_без_опасных_конструкций(self):
        import re
        js = (ПЛАГИН / "dashboard" / "dist" / "index.js").read_text(encoding="utf-8")
        код = re.sub(r"/\*.*?\*/", "", js, flags=re.S)   # без комментариев
        self.assertNotIn("dangerouslySetInnerHTML", код)
        self.assertNotIn("innerHTML", код)
        self.assertNotIn("eval(", код)
        self.assertIn('sandbox: ""', js)              # отчёт в iframe без скриптов
        self.assertIn('register("yadro-guard"', js)

    def test_интерфейс_рендерится_и_решение_уходит(self):
        import shutil, subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js не установлен")
        р = subprocess.run([node, str(КОРЕНЬ / "tests" / "js" / "render_guard_page.mjs"),
                            str(ПЛАГИН / "dashboard" / "dist" / "index.js")],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(0, р.returncode, р.stderr or р.stdout)


if __name__ == "__main__":
    unittest.main()
