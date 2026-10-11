import io
import tempfile
import unittest
from pathlib import Path
from src import autofix
from src.main import компилировать
from src.этика import ЭтическаяОшибка
from src.guard import run, УСПЕХ, НАРУШЕНИЕ_ПОЛИТИКИ


def _диагностика(исходник):
    from src.guard_impl import diagnostic
    try:
        компилировать(исходник)
        return None
    except ЭтическаяОшибка as e:
        return diagnostic(e, "x.яд")


class ТестыАвтофикса(unittest.TestCase):
    def test_обёртка_подбирается_и_проверяется(self):
        код = "функ старт() требует [ДоступСети] {\n  пусть к = среда.секрет()\n  вернуть сеть.отправить(к)\n}"
        план = autofix.предложить(код, _диагностика(код))
        self.assertIsNotNone(план)
        self.assertTrue(план["проверено"])            # исправленный код реально проходит
        self.assertIn("(к)", план["стало"])
        self.assertIn(план["обёртка"] + "(", план["стало"])
        # и главное — переписанный исходник компилируется без ошибки
        компилировать(план["новый_исходник"])

    def test_исправленный_код_проходит_scan(self):
        папка = Path(tempfile.mkdtemp())
        путь = папка / "leak.яд"
        путь.write_text("функ старт() требует [ДоступСети] { вернуть сеть.отправить(пользователь.данные()) }", encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(УСПЕХ, run(["scan", str(путь), "--fix"], out, err))
        fixed = папка / "leak.fixed.яд"
        self.assertTrue(fixed.exists())
        self.assertEqual(УСПЕХ, run(["scan", str(fixed)], io.StringIO(), io.StringIO()))

    def test_нет_обёртки_для_смеси_меток_честно_отказывается(self):
        # Финансы и Локация вместе: пересечение разрешённых обёрток пусто.
        общая = set(autofix.политика.КОМПЛАЕНС["Финансы"]) & set(autofix.политика.КОМПЛАЕНС["Локация"])
        self.assertEqual(set(), общая)  # фиксируем предпосылку
        self.assertIsNone(autofix._выбрать_обёртку(["Финансы", "Локация"]))


if __name__ == "__main__":
    unittest.main()
