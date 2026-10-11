import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from src import vault, guard_api


@unittest.skipUnless(os.name == "nt", "DPAPI есть только в Windows")
class ТестыСейфа(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"YADRO_VAULT_DIR": self.папка})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_секрет_не_лежит_открытым_текстом(self):
        токен = vault.положить("SuperSecret-12345", "УчетныеДанные")
        self.assertTrue(токен.startswith("yg_tok_УчетныеДанные_"))
        сырой = vault.путь_сейфа().read_text(encoding="utf-8")
        self.assertNotIn("SuperSecret-12345", сырой)
        self.assertNotIn("SuperSecret", токен)

    def test_выдача_только_с_мандатом_и_в_журнал(self):
        токен = vault.положить("4111-1111", "Финансы")
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.достать(токен, мандат=False)
        self.assertEqual("4111-1111", vault.достать(токен, мандат=True, причина="аудит"))
        журнал = json.loads(vault.путь_сейфа().read_text(encoding="utf-8"))["audit"]
        self.assertEqual(токен, журнал[-1]["token"])

    def test_список_без_значений_и_забыть(self):
        токен = vault.положить("x", "ПДн")
        записи = vault.список()
        self.assertEqual(["created", "label", "token"], sorted(записи[0]))
        self.assertTrue(vault.забыть(токен))
        self.assertEqual([], vault.список())

    def test_неизвестная_метка_и_повреждённый_блоб(self):
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.положить("x", "Пароль")
        токен = vault.положить("x", "ПДн")
        данные = json.loads(vault.путь_сейфа().read_text(encoding="utf-8"))
        данные["items"][токен]["blob"] = "AAAA"
        vault.путь_сейфа().write_text(json.dumps(данные), encoding="utf-8")
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.достать(токен, мандат=True)


class ТестыFailClosedСейфа(unittest.TestCase):
    def test_без_шифрования_отказ_и_файл_не_пишется(self):
        with tempfile.TemporaryDirectory() as папка, \
                mock.patch.dict(os.environ, {"YADRO_VAULT_DIR": папка}), \
                mock.patch.object(vault, "_шифр_доступен", return_value=False):
            with self.assertRaises(vault.ОшибкаСейфа):
                vault.положить("секрет", "ПДн")
            self.assertFalse(vault.путь_сейфа().exists())


class ТестыGuardApi(unittest.TestCase):
    def файл(self, текст, имя="p.яд"):
        п = Path(tempfile.mkdtemp()) / имя
        п.write_text(текст, encoding="utf-8")
        return str(п)

    def test_утечка_даёт_людские_метки_карантин_и_автофикс(self):
        р = guard_api.анализ(self.файл("функ старт() требует [ДоступСети] {\n  пусть к = среда.секрет()\n  вернуть сеть.отправить(к)\n}"))
        self.assertEqual("leak", р["status"])
        self.assertEqual("Учётные данные и ключи", р["labels"][0]["label"])
        self.assertEqual("отправку в сеть", р["sink"]["human"])
        self.assertTrue(р["quarantine"][0]["options"])
        self.assertTrue(р["autofix"]["проверено"])

    def test_fix_пишет_файл_который_проходит(self):
        путь = self.файл("функ старт() требует [ДоступСети] { вернуть сеть.отправить(пользователь.данные()) }")
        р = guard_api.исправить(путь)
        self.assertEqual("fixed", р["status"])
        self.assertEqual("ok", guard_api.анализ(р["written"])["status"])

    def test_чужое_расширение_отклоняется(self):
        self.assertEqual("error", guard_api.анализ(self.файл("x", "secrets.txt"))["status"])

    def test_cli_всегда_один_json_и_коды(self):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            код = guard_api.main(["scan", self.файл("функ старт() { вернуть 0 }")])
        self.assertEqual(0, код)
        self.assertEqual("ok", json.loads(out.getvalue())["status"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(3, guard_api.main(["bogus"]))
        json.loads(out.getvalue())


if __name__ == "__main__":
    unittest.main()
