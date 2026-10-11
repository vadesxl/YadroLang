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
        self.assertTrue(токен.startswith("yg_tok_Credentials_"))
        self.assertTrue(токен.isascii())
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
        self.assertEqual(["created", "label", "source", "title", "token"], sorted(записи[0]))
        self.assertNotIn("blob", записи[0])                     # шифротекст наружу не отдаётся
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


@unittest.skipUnless(os.name == "nt", "DPAPI есть только в Windows")
class ТестыУправленияСейфом(unittest.TestCase):
    def setUp(self):
        self.папка = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"YADRO_VAULT_DIR": self.папка})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_файл_шифруется_и_сохраняется_копией(self):
        данные = b"OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwx\n"
        токен = vault.положить_файл(данные, "..\\..\\secret<1>.env", "УчетныеДанные")
        сырой = vault.путь_сейфа().read_text(encoding="utf-8")
        self.assertNotIn("sk-proj", сырой)
        запись = [x for x in vault.список(с_корзиной=True) if x["token"] == токен][0]
        self.assertEqual(("file", "secret_1_.env", len(данные)), (запись["kind"], запись["filename"], запись["size"]))
        куда = Path(self.папка) / "out"
        п1, п2 = vault.сохранить_файл(токен, куда), vault.сохранить_файл(токен, куда)
        self.assertEqual(данные, Path(п1).read_bytes())
        self.assertNotEqual(п1, п2)                                  # не перезаписывает
        self.assertTrue(Path(п1).resolve().is_relative_to(куда.resolve()))   # без выхода из папки
        self.assertIn(("OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwx", "Credentials", "secret_1_.env"),
                      vault.known_values())                          # маленький файл ищется в трафике

    def test_переименование_метка_замена_без_смены_токена(self):
        токен = vault.положить("old-value-1", "ПДн")
        vault.переименовать(токен, "  Мой ключ  ")
        vault.сменить_метку(токен, "Финансы")
        vault.заменить(токен, "new-value-2")
        з = [x for x in vault.список() if x["token"] == токен][0]
        self.assertEqual(("Мой ключ", "Financial"), (з["title"], з["label"]))
        self.assertEqual("new-value-2", vault.достать(токен, мандат=True))
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.переименовать(токен, "   ")

    def test_корзина_восстановление_и_окончательное_удаление(self):
        токен = vault.положить("trash-me-123456", "ПДн")
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.удалить_навсегда(токен)                            # сначала корзина
        vault.в_корзину(токен)
        self.assertEqual([], vault.список())
        self.assertNotIn("trash-me-123456", [v[0] for v in vault.known_values()])   # удалённое не ищется
        vault.восстановить(токен)
        self.assertEqual(1, len(vault.список()))
        vault.в_корзину(токен)
        vault.удалить_навсегда(токен)
        self.assertEqual([], vault.список(с_корзиной=True))

    def test_корзина_чистится_через_30_дней(self):
        токен = vault.положить("old", "ПДн")
        vault.в_корзину(токен)
        д = json.loads(vault.путь_сейфа().read_text(encoding="utf-8"))
        д["items"][токен]["deleted"] -= 31 * 86400
        vault.путь_сейфа().write_text(json.dumps(д), encoding="utf-8")
        self.assertEqual([], vault.список(с_корзиной=True))

    def test_операции_через_json_и_лимиты(self):
        import base64, io
        def оп(**к):
            with mock.patch("sys.stdin", io.StringIO(json.dumps(к))):
                return vault.операция_json()
        р = оп(op="file", data=base64.b64encode(b"hello").decode(), filename="a.txt", label="PII")
        self.assertEqual("ok", р["status"])
        self.assertEqual("ok", оп(op="rename", token=р["token"], title="x")["status"])
        self.assertEqual("error", оп(op="replace", token=р["token"], secret="y")["status"])  # файл не текст
        self.assertEqual("error", оп(op="nope")["status"])
        self.assertEqual("error", оп(op="file", data="!!!", filename="a", label="PII")["status"])
        with self.assertRaises(vault.ОшибкаСейфа):
            vault.положить_файл(b"x" * (vault.МАКС_ФАЙЛ + 1), "big.bin", "ПДн")


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
        self.assertTrue(р["autofix"]["verified"])

    def test_английский_исходник_и_ответ(self):
        код = "fn main() requires [NetworkAccess] {\n  let key = env.secret()\n  # \"env.secret\" in text\n  return net.send(key)\n}\n"
        р = guard_api.анализ_текста(код, "en")
        self.assertEqual("leak", р["status"])
        self.assertEqual("en", р["code_language"])
        self.assertEqual(4, р["line"])                         # номер строки исходника пользователя
        self.assertEqual("YADRO-E2301", р["code"])
        self.assertEqual("net.send", р["sink"]["name"])
        self.assertEqual("Credentials & keys", р["labels"][0]["label"])
        self.assertEqual("encrypt", р["autofix"]["wrapper"])
        self.assertIn('"env.secret" in text', р["autofix"]["fixed_code"])  # комментарий не тронут
        self.assertEqual("ok", guard_api.анализ_текста(р["autofix"]["fixed_code"], "en")["status"])
        self.assertTrue(р["known_gaps"])                      # честные ограничения всегда видны

    def test_пустой_и_битый_код_честная_ошибка(self):
        with self.assertRaises(guard_api.ОшибкаВвода):
            guard_api.анализ_текста("   ", "en")
        р = guard_api.анализ_текста("fn main( {", "en")
        self.assertEqual("error", р["status"])
        self.assertTrue(р["message"].startswith("Syntax error"))

    def test_английский_отчёт_экранирует(self):
        р = guard_api.отчёт_текста('fn main() { return 0 }\n# <script>alert(1)</script>', "en")
        self.assertEqual("ok", р["status"])
        self.assertNotIn("<script", р["html"].lower())
        self.assertIn("No leaks found", р["html"])
        self.assertIn("Honest limits", р["html"])

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
