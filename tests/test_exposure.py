import os
import unittest
from src.runtime import exposure as E, services as S

NETSTAT = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1808
  TCP    0.0.0.0:445            0.0.0.0:0              LISTENING       4
  TCP    0.0.0.0:1236           0.0.0.0:0              LISTENING       4340
  TCP    0.0.0.0:5432           0.0.0.0:0              LISTENING       700
  TCP    0.0.0.0:11434          0.0.0.0:0              LISTENING       701
  TCP    127.0.0.1:18434        0.0.0.0:0              LISTENING       22656
  TCP    192.168.1.177:6379     0.0.0.0:0              LISTENING       702
  TCP    192.168.1.177:51000    52.1.1.1:443           ESTABLISHED     900
  TCP    [::]:445               [::]:0                 LISTENING       4
  UDP    0.0.0.0:5353           *:*                                    900
  UDP    127.0.0.1:1900         *:*                                    900
"""
TASKS = '"System","4","Services","0","1 K"\n"svchost.exe","1808","Services","0","1 K"\n' \
        '"AsusUpdateCheck.exe","4340","Services","0","1 K"\n"postgres.exe","700","Console","1","1 K"\n' \
        '"ollama.exe","701","Console","1","1 K"\n"llama-server.exe","22656","Console","1","1 K"\n' \
        '"redis-server.exe","702","Console","1","1 K"\n"chrome.exe","900","Console","1","1 K"\n'


def слушатели(allowed=None):
    имена = E.parse_tasklist(TASKS)
    out = []
    for l in E.parse_netstat(NETSTAT):
        l.process = имена.get(l.pid, "unknown")
        if allowed is not None and E.classify_reach(l.address) != "this_computer":
            l.firewall = "allowed" if l.port in allowed else "not verified"
        out.append(E.assess(l))
    return {(l.address, l.port): l for l in out}


class ТестыЭкспозиции(unittest.TestCase):
    def test_парсинг_только_listening_и_udp(self):
        л = E.parse_netstat(NETSTAT)
        self.assertNotIn(51000, [x.port for x in л])           # ESTABLISHED не слушает
        self.assertIn(("UDP", 5353), [(x.proto, x.port) for x in л])
        self.assertIn("::", [x.address for x in л])

    def test_классы_доступности(self):
        self.assertEqual("all_networks", E.classify_reach("0.0.0.0"))
        self.assertEqual("all_networks", E.classify_reach("::"))
        self.assertEqual("this_computer", E.classify_reach("127.0.0.1"))
        self.assertEqual("this_computer", E.classify_reach("::1"))
        self.assertEqual("local_network", E.classify_reach("192.168.1.177"))
        self.assertEqual("all_networks", E.classify_reach("8.8.8.8"))

    def test_открытая_бд_и_модель_критично(self):
        л = слушатели()
        self.assertEqual(S.CRITICAL, л[("0.0.0.0", 5432)].severity)
        self.assertEqual("PostgreSQL database", л[("0.0.0.0", 5432)].service)
        self.assertEqual(S.CRITICAL, л[("0.0.0.0", 11434)].severity)
        self.assertIn("OLLAMA_HOST=127.0.0.1", л[("0.0.0.0", 11434)].fix)

    def test_localhost_безопасен_даже_для_ии(self):
        л = слушатели()[("127.0.0.1", 18434)]
        self.assertEqual(S.INFO, л.severity)
        self.assertEqual("this_computer", л.reach)
        self.assertEqual("Nothing to do.", л.fix)

    def test_локальная_сеть_на_ступень_ниже(self):
        self.assertEqual(S.HIGH, слушатели()[("192.168.1.177", 6379)].severity)

    def test_системные_windows_не_пугают(self):
        self.assertEqual(S.INFO, слушатели()[("0.0.0.0", 135)].severity)
        self.assertEqual(S.MEDIUM, слушатели()[("0.0.0.0", 445)].severity)     # SMB честно отмечен
        self.assertEqual(S.MEDIUM, слушатели()[("0.0.0.0", 1236)].severity)    # служба ASUS

    def test_брандмауэр_явно_разрешает_открытую_бд(self):
        л = слушатели(allowed={5432})[("0.0.0.0", 5432)]
        self.assertEqual(S.CRITICAL, л.severity)          # риск не занижается по догадкам
        self.assertIn("firewall-allows", л.tags)

    def test_udp_обнаружение_не_шумит(self):
        л = слушатели()[("0.0.0.0", 5353)]
        self.assertEqual(S.INFO, л.severity)
        self.assertEqual("Nothing to do.", л.fix)

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_живой_скан_этой_машины(self):
        р = E.scan(with_firewall=False)
        self.assertEqual("ok", р["status"])
        self.assertTrue(р["listeners"])
        self.assertTrue(0 <= р["score"] <= 100)
        self.assertTrue(all(x["reach"] in ("this_computer", "local_network", "all_networks") for x in р["listeners"]))
        self.assertTrue(р["limits"])


if __name__ == "__main__":
    unittest.main()
