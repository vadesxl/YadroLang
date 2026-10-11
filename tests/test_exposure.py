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

    # ---- брандмауэр: вердикт из локальной политики ----
    @staticmethod
    def _fw(rules, default_in=(1, 1, 1), current=2, enabled=(True, True, True), modify=0, block_all=(False,) * 3):
        return {"current": current, "modify_state": modify, "enabled": list(enabled),
                "default_in": list(default_in), "block_all": list(block_all), "rules": rules, "paths": {}}

    @staticmethod
    def _rule(**kw):
        r = {"name": "r", "action": 1, "protocol": 6, "ports": "*", "app": None, "service": None,
             "profiles": 2147483647, "remote": "*", "local": "*", "ifaces": "All", "group": None, "package": False}
        r.update(kw)
        return r

    def _l(self, port=5432, proto="TCP", process="postgres.exe"):
        return E.Listener(proto, "0.0.0.0", port, 700, process=process)

    def test_fw_правило_программы_по_пути_разрешает(self):
        fw = self._fw([self._rule(name="PG", app=r"C:\PG\postgres.exe", remote="LocalSubnet")])
        v = E.firewall_verdict(self._l(), fw, [], r"c:\pg\POSTGRES.exe")
        self.assertEqual(("allowed", "PG", "local network"), v)

    def test_fw_чужая_программа_не_считается(self):
        fw = self._fw([self._rule(app=r"C:\Other\x.exe")], default_in=(0, 0, 0))
        self.assertEqual("blocked", E.firewall_verdict(self._l(), fw, [], r"C:\PG\postgres.exe")[0])

    def test_fw_по_умолчанию_блок_без_правил(self):
        self.assertEqual(("blocked", "", "default"), E.firewall_verdict(self._l(), self._fw([], (0, 0, 0)), [], ""))

    def test_fw_выключен_и_групповая_политика(self):
        self.assertEqual("off", E.firewall_verdict(self._l(), self._fw([], enabled=(True, False, True)), [], "")[0])
        self.assertEqual("not verified", E.firewall_verdict(self._l(), self._fw([], modify=1), [], "")[0])
        self.assertEqual("not verified", E.firewall_verdict(self._l(), None, [], "")[0])

    def test_fw_блок_с_ограничениями_не_выдаётся_за_блок(self):
        # блок только для части адресов (как правило песочницы) -> честно "not verified"
        fw = self._fw([self._rule(action=0, protocol=256, ports=None, remote="0.0.0.0-126.255.255.255")], (0, 0, 0))
        self.assertEqual("not verified", E.firewall_verdict(self._l(), fw, [], "")[0])

    def test_fw_ключевые_слова_портов_и_wfd_не_решают(self):
        fw = self._fw([self._rule(app="System", ports="IPHTTPS"),
                       self._rule(app="System", group="@wlansvc.dll,-36865")], (0, 0, 0))
        self.assertEqual("not verified", E.firewall_verdict(self._l(445, process="System"), fw, [], "")[0])

    def test_fw_правило_store_приложений_не_касается_обычных_программ(self):
        fw = self._fw([self._rule(name="Xbox", protocol=256, package=True)], (0, 0, 0))
        self.assertEqual("blocked", E.firewall_verdict(self._l(), fw, [], r"C:\PG\postgres.exe")[0])

    def test_fw_служба_и_диапазон_портов(self):
        fw = self._fw([self._rule(name="NTP", protocol=17, ports="100-200", service="W32Time")], (0, 0, 0))
        л = self._l(123, "UDP", "svchost.exe")
        self.assertEqual("allowed", E.firewall_verdict(л, fw, ["W32Time"], "")[0])
        self.assertEqual("blocked", E.firewall_verdict(л, fw, ["Dnscache"], "")[0])

    # ---- IPv4 + IPv6 в одной строке, svchost по имени службы ----
    def test_ipv4_и_ipv6_сливаются(self):
        л = E.parse_netstat(NETSTAT)
        for x in л:
            x.process = "System"
            E.assess(x)
        слитые = [x for x in E.merge_dual_stack(л) if x.port == 445]
        self.assertEqual(1, len(слитые))
        self.assertEqual(["0.0.0.0", "::"], слитые[0].addresses)

    def test_слияние_берёт_худший_вердикт(self):
        a, b = self._l(), self._l()
        b.address = "::"
        a.firewall, b.firewall, b.firewall_rule = "blocked", "allowed", "X"
        for x in (a, b):
            E.assess(x)
        м = E.merge_dual_stack([a, b])
        self.assertEqual(1, len(м))
        self.assertEqual(("allowed", "X"), (м[0].firewall, м[0].firewall_rule))

    def test_svchost_123_это_служба_времени(self):
        л = E.Listener("UDP", "0.0.0.0", 123, 37212, process="svchost.exe", services=["W32Time"])
        E.assess(л)
        self.assertEqual("Windows Time (NTP)", л.service)
        self.assertEqual(S.INFO, л.severity)

    def test_parse_services(self):
        т = '"svchost.exe","37212","W32Time"\n"System","4","N/A"\n"svchost.exe","1808","RpcEptMapper,RpcSs"\n'
        self.assertEqual({37212: ["W32Time"], 1808: ["RpcEptMapper", "RpcSs"]}, E.parse_services(т))

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
