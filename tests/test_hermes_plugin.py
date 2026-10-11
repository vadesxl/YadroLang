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

    def тело(self, путь):
        return self.api.PathBody(path=путь)

    def test_манифест_как_у_hermes(self):
        м = json.loads((ПЛАГИН / "dashboard" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("yadro-guard", м["name"])
        for ключ in ("entry", "css", "api", "tab"):
            self.assertIn(ключ, м)
        for файл in (м["entry"], м["css"], м["api"]):
            self.assertTrue((ПЛАГИН / "dashboard" / файл).exists(), файл)

    def test_scan_через_бэкенд_и_история(self):
        прог = self.папка / "leak.яд"
        прог.write_text("функ старт() требует [ДоступСети] { вернуть сеть.отправить(среда.секрет()) }", encoding="utf-8")
        р = asyncio.run(self.api.scan(self.тело(str(прог))))
        self.assertEqual("leak", р["status"])
        self.assertEqual("Учётные данные и ключи", р["labels"][0]["label"])
        история = asyncio.run(self.api.history())["items"]
        self.assertEqual(str(прог), история[0]["path"])
        self.assertNotIn("секрет", json.dumps(история, ensure_ascii=False).replace("среда.секрет", ""))

    def test_отклоняет_чужие_файлы_и_относительные_пути(self):
        self.assertEqual("error", asyncio.run(self.api.scan(self.тело("C:\\Windows\\win.ini")))["status"])
        self.assertEqual("error", asyncio.run(self.api.scan(self.тело("leak.яд")))["status"])

    def test_без_настройки_честная_ошибка(self):
        (self.папка / "config.json").unlink()
        self.assertEqual("error", asyncio.run(self.api.scan(self.тело("C:\\x.яд")))["status"])
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


if __name__ == "__main__":
    unittest.main()
