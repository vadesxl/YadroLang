import unittest

from src.main import компилировать,ОшибкаГлубиныАрифметики


class CheckedArithmeticDepthTests(unittest.TestCase):
    def left_deep(self, tail):
        return "9223372036854775807" + " + 0" * 257 + tail

    def test_checked_constant_analysis_exhaustion_fails_closed(self):
        source = f"функ старт() {{ вернуть {self.left_deep(' + 1')} }}"
        with self.assertRaises(ОшибкаГлубиныАрифметики) as caught:
            компилировать(source, арифметика="checked")
        self.assertEqual("ЯДРО-А1002", caught.exception.код)
        self.assertIn("строка 1", str(caught.exception))

    def test_deep_constant_divisor_cannot_hide_zero(self):
        divisor = "0" + " + 0" * 257
        source = f"функ старт() {{ вернуть 1 / ({divisor}) }}"
        with self.assertRaises(ОшибкаГлубиныАрифметики) as caught:
            компилировать(source)
        self.assertEqual("ЯДРО-А1002", caught.exception.код)

    def test_nonconstant_checked_expression_still_uses_runtime_guard(self):
        source = "функ calc(x) { вернуть x + 1 } функ старт() { вернуть calc(1) }"
        text = компилировать(source, арифметика="checked")
        self.assertIn("with.overflow.i64", text)


if __name__ == "__main__":
    unittest.main()
