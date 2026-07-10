import io
import json
import tempfile
import unittest
from src.mcp_guard import run, EXIT_OK, EXIT_POLICY


class ТестыMcpGuard(unittest.TestCase):
    def manifest(self,data):
        файл=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8"); json.dump(data,файл,ensure_ascii=False); файл.close(); return файл.name

    def test_утечка_пдн(self):
        путь=self.manifest({"version":"1.0","tools":[{"name":"crm.читать","labels":["ПДн"]},{"name":"сеть.отправить","capabilities":["ДоступСети"]}],"flows":[["crm.читать","сеть.отправить"]]})
        self.assertEqual(EXIT_POLICY,run(["scan",путь],io.StringIO(),io.StringIO()))

    def test_секреты_и_excessive_agency(self):
        путь=self.manifest({"version":"1.0","tools":[{"name":"секрет.читать","labels":["УчетныеДанные"]},{"name":"агент.запустить","capabilities":["ДоступСети","ВыполнениеИнструмента","ДоступСекретов"]}],"flows":[["секрет.читать","агент.запустить"]]})
        out=io.StringIO(); self.assertEqual(EXIT_POLICY,run(["scan",путь,"--format","json"],out,io.StringIO()))
        self.assertEqual({"ЯДРО-MCP-2301","ЯДРО-MCP-2401"},{i["code"] for i in json.loads(out.getvalue())["findings"]})

    def test_безопасный_санитизированный_поток(self):
        путь=self.manifest({"version":"1.0","tools":[{"name":"crm.читать","labels":["ПДн"]},{"name":"privacy.редактировать","sanitizes":["ПДн"]},{"name":"сеть.отправить","capabilities":["ДоступСети"]}],"flows":[["crm.читать","privacy.редактировать"],["privacy.редактировать","сеть.отправить"]]})
        self.assertEqual(EXIT_OK,run(["scan",путь],io.StringIO(),io.StringIO()))


if __name__=="__main__": unittest.main()
