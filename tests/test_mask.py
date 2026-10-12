import unittest

from src.runtime.detectors import MAX_SHOWN, mask, scan_text

GH = "gh" + "p_" + "8a2bZ9y8X7w6V5u4T3s2R1q0P9o8N7m6L59c"


def _shown(preview: str) -> int:
    return len(preview.replace("*", "").replace(" ", "").replace("•", ""))


class MaskTests(unittest.TestCase):
    def test_token_keeps_type_prefix(self):
        self.assertEqual("ghp_8a2b***9c", mask(GH, "github_token"))
        self.assertEqual("ghp_8a2b***9c", next(f for f in scan_text(f"token {GH}")).preview)

    def test_card_shows_last_four_only(self):
        self.assertEqual("**** 4432", mask("4111 1111 1111 4432", "card_number"))

    def test_email_iban_url(self):
        self.assertEqual("j***@example.com", mask("john.smith@example.com", "email"))
        self.assertEqual("DE89 **** 3000", mask("DE89370400440532013000", "iban"))
        self.assertEqual("https://admin:***@db.example", mask("https://admin:hunter22@db.example", "password_in_url"))

    def test_key_bodies_are_never_shown(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAsecretbody\n-----END RSA PRIVATE KEY-----"
        p = mask(pem, "private_key")
        self.assertNotIn("MIIE", p)
        self.assertTrue(p.startswith("[-----BEGIN RSA PRIVATE KEY") and "chars]" in p)
        self.assertEqual("[60 chars]", mask("{" + "1," * 29 + "}", "solana_keypair")[:10])

    def test_seed_phrase(self):
        seed = " ".join(["abandon"] * 11 + ["about"])
        self.assertEqual("abandon ••• about (12 words)", mask(seed, "seed_phrase"))

    def test_short_values_fully_hidden(self):
        self.assertEqual("••••••", mask("hunter"))
        self.assertEqual("ab***yz", mask("abcdefghijwxyz"))

    def test_never_more_than_40_percent(self):
        for v, k in ((GH, "github_token"), ("AKIA" + "ABCDEFGHIJKLMNOP", "aws_access_key"), ("sk-" + "x" * 12, ""),
                     ("4111111111114432", "card_number"), ("x" * 9, ""), ("y" * 40, "")):
            p = mask(v, k)
            self.assertLessEqual(_shown(p), MAX_SHOWN * len(v), (v, p))


if __name__ == "__main__":
    unittest.main()
