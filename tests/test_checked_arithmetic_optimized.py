import unittest

from llvmlite import binding as llvm

from src.main import компилировать


class CheckedArithmeticOptimizedIrTests(unittest.TestCase):
    def optimized(self, source):
        module = llvm.parse_assembly(компилировать(source, арифметика="checked"))
        module.verify()
        builder = llvm.create_pass_manager_builder()
        builder.opt_level = 2
        manager = llvm.create_module_pass_manager()
        builder.populate(manager)
        manager.run(module)
        module.verify()
        return str(module)

    def test_overflow_guards_survive_o2(self):
        for operator in ("+", "-", "*"):
            with self.subTest(operator=operator):
                text = self.optimized(
                    f"функ calc(x) {{ вернуть x {operator} 2 }} "
                    "функ старт() { вернуть calc(3) }"
                )
                self.assertIn("with.overflow.i64", text)
                self.assertIn("llvm.trap", text)
                self.assertIn("unreachable", text)

    def test_division_guards_survive_o2(self):
        text = self.optimized(
            "функ calc(x, y) { вернуть x / y } "
            "функ старт() { вернуть calc(8, 2) }"
        )
        self.assertIn("llvm.trap", text)
        self.assertIn("sdiv i64", text)
        self.assertIn("icmp eq i64", text)


if __name__ == "__main__":
    unittest.main()
