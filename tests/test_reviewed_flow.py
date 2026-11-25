"""Behavioral regressions found while reviewing the preserved fix branches."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from src.main import компилировать as compile
from src.этика import ЭтическаяОшибка as EthicalError
from src.типы import ОшибкаТипов as TypeCheckError

from src.guard_cli import run

class ReviewedFlowTests(unittest.TestCase):
    def test_helper_branch_assignment(self):
        with self.assertRaises(EthicalError):
            compile('функ helper(value, flag) требует [ДоступСети] { пусть x = 0 если flag { x = value } иначе { x = 0 } сеть.отправить(x) вернуть 0 } функ старт() требует [ДоступСети] { helper(пользователь.данные(), 1) вернуть 0 }')

    def test_helper_branch_control(self):
        with self.assertRaises(EthicalError):
            compile('функ helper(flag) требует [ДоступСети] { пусть x = 0 если flag { x = 1 } сеть.отправить(x) вернуть 0 } функ старт() требует [ДоступСети] { helper(пользователь.данные()) вернуть 0 }')

    def test_transitive_control_summary(self):
        with self.assertRaises(EthicalError):
            compile('функ relay(flag) требует [ДоступСети] { если flag { emit() } вернуть 0 } функ emit() требует [ДоступСети] { сеть.отправить(1) вернуть 0 } функ старт() требует [ДоступСети] { relay(пользователь.данные()) вернуть 0 }')

    def test_entry_return(self):
        with self.assertRaises(EthicalError):
            compile('функ старт() { вернуть среда.секрет() }')

    def test_entry_helper_return(self):
        with self.assertRaises(EthicalError):
            compile('функ helper() { вернуть среда.секрет() } функ старт() { вернуть helper() }')

    def test_entry_implicit_return(self):
        with self.assertRaises(EthicalError):
            compile('функ старт() { если среда.секрет() { вернуть 1 } иначе { вернуть 0 } }')

    def test_entry_implicit_assignment(self):
        with self.assertRaises(EthicalError):
            compile('функ helper() { вернуть 1 } функ старт() { пусть s = среда.секрет() пусть k = 0 если s { k = helper() } вернуть k }')

    def test_helper_branch_sanitization(self):
        compile('функ helper(value, flag) требует [ДоступСети] { если flag { value = анонимизировать(value) } иначе { value = анонимизировать(value) } сеть.отправить(value) вернуть 0 } функ старт() требует [ДоступСети] { helper(пользователь.данные(), 1) вернуть 0 }')

    def test_entry_sanitized_return(self):
        compile('функ старт() { вернуть анонимизировать(пользователь.данные()) }')

    def test_entry_clean(self):
        compile('функ старт() { печать(1) }')

    def test_audit_checks_entry_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'case.яд'
            path.write_text('функ старт() { вернуть среда.секрет() }', encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            self.assertEqual(2, run(["audit", str(path), "--format", "json"], stdout, stderr))
            self.assertEqual('ЯДРО-Э2301', json.loads(stderr.getvalue())["code"])

    def test_missing_return_rejected_before_codegen(self):
        with mock.patch("src.main.Кодоген") as backend:
            with self.assertRaises(TypeCheckError):
                compile('функ helper(x) { если x { вернуть 1 } } функ старт() { вернуть helper(1) }')
            backend.assert_not_called()
