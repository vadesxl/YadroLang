import ctypes
import random
import unittest

from llvmlite import binding as llvm

from src.abi import symbol
from src.main import I64_МИН, I64_МАКС, компилировать

MASK = 2**64 - 1
SEED = 0x594144524F
CASES = 160


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
        if tree == I64_МИН:
            return "((0 - 9223372036854775807) - 1)"
        return str(tree) if tree >= 0 else f"(0 - {abs(tree)})"
    op, left, right = tree
    return f"({source(left)} {op} {source(right)})"


def generate(rng, depth):
    leaves = [0, 1, 2, 3, 7, 31, 2**31 - 1, I64_МАКС, -1, -2, I64_МИН]
    if depth == 0 or rng.random() < 0.28:
        return rng.choice(leaves)
    tree = (rng.choice(("+", "-", "*", "/")), generate(rng, depth - 1), generate(rng, depth - 1))
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

    def test_seeded_random_expressions_match_llvm_i64(self):
        rng = random.Random(SEED)
        trees = [generate(rng, 4) for _ in range(CASES)]
        functions = " ".join(
            f"функ calc{index}() {{ вернуть {source(tree)} }}"
            for index, tree in enumerate(trees)
        )
        ir = компилировать(functions + " функ старт() { вернуть 0 }")
        module = llvm.parse_assembly(ir)
        module.verify()
        backing = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing, self.machine)
        engine.add_module(module)
        engine.finalize_object()
        for index, tree in enumerate(trees):
            expression = source(tree)
            with self.subTest(index=index, expression=expression):
                address = engine.get_function_address(symbol("fn", f"calc{index}"))
                self.assertNotEqual(0, address)
                actual = ctypes.CFUNCTYPE(ctypes.c_int64)(address)()
                self.assertEqual(evaluate(tree), actual)
        engine.remove_module(module)


if __name__ == "__main__":
    unittest.main()
