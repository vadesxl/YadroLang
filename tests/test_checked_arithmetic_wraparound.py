import unittest

from src.main import компилировать,ОшибкаСемантики


class CheckedArithmeticWraparoundTests(unittest.TestCase):
    def test_default_constant_divisor_that_wraps_to_zero_is_rejected(self):
        source = (
            "функ старт() { вернуть 1 / "
            "((9223372036854775807 + 1) * 2) }"
        )
        with self.assertRaisesRegex(ОшибкаСемантики, "Деление на ноль"):
            компилировать(source)

    def test_default_wrapped_dividend_hits_int_min_overflow_rule(self):
        source = (
            "функ старт() { вернуть "
            "((9223372036854775807 + 1) / (0 - 1)) }"
        )
        with self.assertRaisesRegex(ОшибкаСемантики, "Переполнение знакового i64"):
            компилировать(source)

    def test_default_nonzero_wrapped_divisor_remains_allowed(self):
        source = (
            "функ старт() { вернуть 2 / "
            "((9223372036854775807 + 1) * 2 + 1) }"
        )
        text = компилировать(source)
        self.assertIn("sdiv i64", text)


if __name__ == "__main__":
    unittest.main()
