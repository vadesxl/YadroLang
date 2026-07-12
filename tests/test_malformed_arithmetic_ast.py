import unittest

from src.кодоген import Кодоген
from src.синтаксис import Бинарный,Вернуть,Функция,Программа,Число
from src.типы import ОшибкаТипов


class MalformedArithmeticAstTests(unittest.TestCase):
    def program(self, value):
        literal = Число(1, value)
        expression = Бинарный(1, "+", literal, Число(1, 1))
        return Программа(0, [Функция(1, "старт", [], [Вернуть(1, expression)], [])])

    def test_bool_is_not_accepted_as_integer_literal(self):
        with self.assertRaises(ОшибкаТипов) as caught:
            Кодоген(arithmetic_profile="checked").сгенерировать(self.program(True))
        self.assertEqual("ЯДРО-Т2010", caught.exception.код)

    def test_float_string_none_and_object_are_controlled_errors(self):
        for value in (1.5, "1", None, object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ОшибкаТипов) as caught:
                    Кодоген(arithmetic_profile="checked").сгенерировать(self.program(value))
                self.assertEqual("ЯДРО-Т2010", caught.exception.код)

    def test_direct_ast_literal_outside_i64_is_rejected_before_llvm(self):
        for value in (-(2**63)-1, 2**63):
            with self.subTest(value=value):
                with self.assertRaises(ОшибкаТипов) as caught:
                    Кодоген(arithmetic_profile="checked").сгенерировать(self.program(value))
                self.assertEqual("ЯДРО-Т2011", caught.exception.код)


if __name__ == "__main__":
    unittest.main()
