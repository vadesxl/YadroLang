import ctypes
import random
import unittest

from llvmlite import binding as llvm

from src.abi import symbol
from src.main import I64_МИН, I64_МАКС, компилировать

MASK = 2**64 - 1
SEED = 0x594144524F


def wrap(value):
    value &= MASK
    return value - 2**64 if value >= 2**63 else value


def trunc_div(left, right):
    return abs(left) // abs(right) * (-1 if (left < 0) != (right < 0) else 1)


def evaluate(tree):
    if isinstance(tree, int):
        return tree
    op, left_tree, right_tree = tree
    left, right = evaluate(left_tree), evaluate(right_tree)
    if op == "+":
        return wrap(left + right)
    if op == "-":
        return wrap(left - right)
    if op == "*":
        return wrap(left * right)
    if right == 0 or (left == I64_МИН and right == -1):
        raise ArithmeticError
    return trunc_div(left, right)


def source(tree):
    if isinstance(tree, int):
        return str(tree) if tree >= 0 else f"(0 - {abs(tree)})"
    op, left, right = tree
    return f"({source(left)} {op} {source(right)})"


def generate(rng, depth):
    leaves = [0, 1, 2, 3, 7, 31, 2**31 - 1, I64_МАКС, -1, -2, I64_МИН]
    if depth == 0 or rng.random() < 0.28:
        return rng.choice(leaves)
    op = rng.choice(("+", "-", "*", "/"))
    left, right = generate(rng, depth - 1), generate(rng, depth - 1)
    tree = (op, left, right)
    try:
        evaluate(tree)
    except ArithmeticError:
        return generate(rng, depth - 1)
    return tree


class ArithmeticDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for initializer in (
            getattr(llvm, "initialize", None),
            getattr(llvm, "initialize_native_target", None),
            getattr(llvm, "initialize_native_asmprinter", None),
        ):
            if initializer:
                try:
                    initializer()
                except RuntimeError:
                    pass
        cls.machine = llvm.Target.from_default_triple().create_target_machine()

    def execute(self, expression):
        ir = компилировать(
            f"функ calc() {{ вернуть {expression} }} функция старт() {{ вернуть 0 }}".replace("функция", "функ")
        )
        module = llvm.parse_assembly(ir)
        module.verify()
        backing = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing, self.machine)
        engine.add_module(module)
        engine.finalize_object()
        address = engine.get_function_address(symbol("fn", "calc"))
        self.assertNotEqual(0, address)
        result = ctypes.CFUNCTYPE(ctypes.c_int64)(address)()
        engine.remove_module(module)
        return result

    def test_seeded_random_expressions_match_llvm_i64(self):
        rng = random.Random(SEED)
        for index in range(160):
            tree = generate(rng, 4)
            expression = source(tree)
            with self.subTest(index=index, expression=expression):
                self.assertEqual(evaluate(tree), self.execute(expression))


if __name__ == "__main__":
    unittest.main()
