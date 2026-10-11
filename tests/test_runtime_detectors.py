import unittest
from src.runtime import detectors as d

# Синтетические значения, собранные во время выполнения: в исходнике нет
# цельных токенов, чтобы secret scanners на GitHub не поднимали тревогу.
GH = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
AWS = "AK" + "IA" + "QWERTYUIOP123456"
GOOGLE = "AI" + "za" + "Sy" + "A" * 10 + "b" * 10 + "C" * 13
CARD = "4111 1111 1111 1111"
IBAN = "CH93 0076 2011 6238 5295 7"


def kinds(text, **kw):
    return [f.kind for f in d.scan_text(text, **kw)]


class ТестыДетекторов(unittest.TestCase):
    def test_токены_провайдеров(self):
        self.assertEqual(["github_token"], kinds(f"curl -H 'x: {GH}' api"))
        self.assertEqual(["aws_access_key"], kinds(f"key={AWS}"))
        self.assertEqual(["google_api_key"], kinds(f"?k={GOOGLE}"))

    def test_карта_только_с_верной_контрольной_суммой(self):
        self.assertEqual(["card_number"], kinds(f"pay {CARD} now"))
        self.assertEqual([], kinds("order 4111 1111 1111 1112"))        # Luhn не сходится
        self.assertEqual([], kinds("phone 0000 0000 0000 0000"))        # мусор

    def test_iban_с_mod97(self):
        self.assertEqual(["iban"], kinds(f"to {IBAN}"))
        self.assertEqual([], kinds("to CH93 0076 2011 6238 5295 8"))

    def test_пароль_в_url_и_bearer(self):
        self.assertEqual(["password_in_url"], kinds("postgres://admin:Sup3rS3cret@db:5432/x"))
        ф = d.scan_text("Authorization: Bearer abcDEF123ghiJKL456mnoPQR789stu")
        self.assertEqual("generic_secret", ф[0].kind)

    def test_низкая_энтропия_и_примеры_не_ловятся(self):
        self.assertEqual([], kinds("password = aaaaaaaaaaaaaaaaaaaa"))
        self.assertEqual([], kinds("api_key = your_api_key_here_please"))

    def test_секрет_из_сейфа_приоритетнее(self):
        ф = d.scan_text("send my-own-value-42 now", known_secrets=[("my-own-value-42", "Credentials", "")])
        self.assertEqual(["vault_secret"], [x.kind for x in ф])
        self.assertEqual("certain", ф[0].confidence)

    def test_превью_маскирует_значение(self):
        ф = d.scan_text(f"x {GH}")[0]
        self.assertNotIn(GH, str(ф.public()))
        self.assertTrue(ф.preview.startswith("ghp_") and "…" in ф.preview)

    def test_вложенные_аргументы_и_редактирование(self):
        args = {"url": "https://api.x", "headers": {"Authorization": f"token {GH}"}, "body": [f"card {CARD}"]}
        ф = d.scan_args(args)
        self.assertEqual({"headers.Authorization", "body[0]"}, {x.path for x in ф})
        чистые = d.redact_args(args, ф, lambda f: "[REDACTED]")
        self.assertEqual("token [REDACTED]", чистые["headers"]["Authorization"])
        self.assertEqual("card [REDACTED]", чистые["body"][0])
        self.assertEqual(f"token {GH}", args["headers"]["Authorization"])  # оригинал не тронут
        self.assertEqual([], d.scan_args(чистые))


if __name__ == "__main__":
    unittest.main()
