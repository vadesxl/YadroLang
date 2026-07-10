import io,json,tempfile,unittest
from src.guard_cli import run
from src.mcp_guard_v2 import MAX_BYTES,MAX_TOOLS
class ТестыMcpV2(unittest.TestCase):
 def manifest(self,data=None,raw=None):
  f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8");f.write(raw if raw is not None else json.dumps(data,ensure_ascii=False));f.close();return f.name
 def scan(self,data,fmt=None):
  out,err=io.StringIO(),io.StringIO();args=["mcp","scan",self.manifest(data)]+(["--format",fmt] if fmt else []);code=run(args,out,err);return code,out.getvalue(),err.getvalue()
 def test_unknown_fields_and_capabilities_rejected(self):
  for data in ({"version":"1.0","tools":[],"oops":1},{"version":"1.0","tools":[{"name":"x","capabilities":["Root"]}]}):self.assertEqual(3,self.scan(data)[0])
 def test_malformed_collection_types_are_source_errors(self):
  cases=[{"version":"1.0","tools":[{"name":"x","labels":"ПДн"}]},{"version":"1.0","tools":[{"name":"x","labels":[{}]}]},{"version":"1.0","tools":[],"flows":{}},{"version":"1.0","tools":[],"policy":[]}]
  for data in cases:
   with self.subTest(data=data):self.assertEqual(3,self.scan(data)[0])
 def test_duplicate_tools_values_and_edges_rejected(self):
  cases=[{"version":"1.0","tools":[{"name":"x"},{"name":"x"}]},{"version":"1.0","tools":[{"name":"x","labels":["ПДн","ПДн"]}]},{"version":"1.0","tools":[{"name":"a"},{"name":"b"}],"flows":[["a","b"],["a","b"]]}]
  for data in cases:
   with self.subTest(data=data):self.assertEqual(3,self.scan(data)[0])
 def test_file_size_and_tool_count_are_bounded(self):
  path=self.manifest(raw=" "*(MAX_BYTES+1));self.assertEqual(3,run(["mcp","scan",path],io.StringIO(),io.StringIO()))
  data={"version":"1.0","tools":[{"name":f"t{i}"} for i in range(MAX_TOOLS+1)]};self.assertEqual(3,self.scan(data)[0])
 def test_cycle_reaches_worklist_fixpoint_and_order_is_deterministic(self):
  data={"version":"1.0","tools":[{"name":"b","capabilities":["ДоступСети"]},{"name":"a","labels":["ПДн"]}],"flows":[["a","b"],["b","a"]]};first=self.scan(data,"json");second=self.scan(data,"json");self.assertEqual(2,first[0]);self.assertEqual(first[1],second[1]);payload=json.loads(first[1]);self.assertEqual(["b"],[item["tool"] for item in payload["findings"]]);self.assertLessEqual(payload["summary"]["fixpoint_updates"],2)
 def test_long_graph_stays_bounded(self):
  tools=[{"name":f"t{i}",**({"labels":["ПДн"]} if i==0 else {}),**({"capabilities":["ДоступСети"]} if i==MAX_TOOLS-1 else {})} for i in range(MAX_TOOLS)];flows=[[f"t{i}",f"t{i+1}"] for i in range(MAX_TOOLS-1)];code,out,_=self.scan({"version":"1.0","tools":tools,"flows":flows},"json");self.assertEqual(2,code);self.assertLessEqual(json.loads(out)["summary"]["fixpoint_updates"],MAX_TOOLS*5)
 def test_custom_policy_is_isolated_between_runs(self):
  tool={"name":"send","labels":["ПДн"],"capabilities":["ДоступСети"]};relaxed={"version":"1.0","tools":[tool],"policy":{"privileged_capabilities":[],"max_capabilities_per_tool":7}};strict={"version":"1.0","tools":[tool]};self.assertEqual(0,self.scan(relaxed)[0]);self.assertEqual(2,self.scan(strict)[0]);self.assertEqual(0,self.scan(relaxed)[0])
 def test_quiet_preserves_exit_without_output(self):
  path=self.manifest({"version":"1.0","tools":[],"flows":[]});out=io.StringIO();self.assertEqual(0,run(["mcp","scan",path,"--quiet"],out,io.StringIO()));self.assertEqual("",out.getvalue())
 def test_sarif_is_valid_for_zero_findings(self):
  code,out,_=self.scan({"version":"1.0","tools":[],"flows":[]},"sarif");payload=json.loads(out);self.assertEqual(0,code);self.assertEqual("2.1.0",payload["version"]);self.assertEqual([],payload["runs"][0]["results"])
if __name__=="__main__":unittest.main()
