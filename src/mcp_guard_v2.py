# -*- coding: utf-8 -*-
"""Bounded deterministic scanner for Yadro-specific MCP security schema."""
import argparse,json,sys
from pathlib import Path
EXIT_OK,EXIT_POLICY,EXIT_SOURCE,EXIT_INTERNAL=0,2,3,4
LABELS=frozenset({"ПДн","Финансы","Здоровье","УчетныеДанные","Локация"})
CAPABILITIES=frozenset({"ДоступСети","ЗаписьДиска","ЗаписьБД","ЧтениеБД","ВыполнениеИнструмента","ДоступСекретов","ДоступЛог"})
ROOT_KEYS=frozenset({"version","tools","flows"});TOOL_KEYS=frozenset({"name","labels","sanitizes","capabilities"});MAX_TOOLS=10000
class ManifestError(ValueError):pass
def _unknown(mapping,allowed,where):
 unknown=sorted(set(mapping)-allowed)
 if unknown:raise ManifestError(f"неизвестные поля {where}: {', '.join(unknown)}")
def load(path):
 data=json.loads(Path(path).read_text(encoding="utf-8"))
 if not isinstance(data,dict):raise ManifestError("корень manifest должен быть объектом")
 _unknown(data,ROOT_KEYS,"manifest")
 if data.get("version")!="1.0" or not isinstance(data.get("tools"),list):raise ManifestError("нужны version '1.0' и tools")
 if len(data["tools"])>MAX_TOOLS:raise ManifestError(f"слишком много tools, максимум {MAX_TOOLS}")
 tools={}
 for raw in data["tools"]:
  if not isinstance(raw,dict):raise ManifestError("каждый tool должен быть объектом")
  _unknown(raw,TOOL_KEYS,"tool");name=raw.get("name")
  if not isinstance(name,str) or not name.strip():raise ManifestError("каждому tool нужно имя")
  if name in tools:raise ManifestError(f"повторный tool: {name}")
  labels,sanitizes,capabilities=set(raw.get("labels",[])),set(raw.get("sanitizes",[])),set(raw.get("capabilities",[]))
  if not labels<=LABELS or not sanitizes<=LABELS:raise ManifestError(f"неизвестная метка: {name}")
  if not capabilities<=CAPABILITIES:raise ManifestError(f"неизвестная capability: {name}")
  tools[name]={"labels":labels,"sanitizes":sanitizes,"capabilities":capabilities}
 edges=set()
 for edge in data.get("flows",[]):
  if not isinstance(edge,list) or len(edge)!=2 or edge[0] not in tools or edge[1] not in tools:raise ManifestError(f"неверное ребро: {edge!r}")
  edges.add((edge[0],edge[1]))
 return tools,sorted(edges)
def analyze(tools,edges):
 state={name:set(tool["labels"]) for name,tool in tools.items()}
 for _ in range(len(tools)*len(LABELS)+1):
  changed=False
  for source,target in edges:
   merged=state[target]|(state[source]-tools[target]["sanitizes"])
   if merged!=state[target]:state[target]=merged;changed=True
  if not changed:break
 else:raise RuntimeError("MCP fixpoint bound exceeded")
 incoming={name:0 for name in tools}
 for _,target in edges:incoming[target]+=1
 findings=[]
 for name in sorted(tools):
  dangerous=tools[name]["capabilities"]&CAPABILITIES
  if state[name] and dangerous:findings.append({"code":"ЯДРО-MCP-2301","severity":"error","tool":name,"labels":sorted(state[name]),"capabilities":sorted(dangerous),"message":f"Чувствительные данные достигают MCP tool '{name}'"})
  if len(dangerous)>=3:findings.append({"code":"ЯДРО-MCP-2401","severity":"error","tool":name,"capabilities":sorted(dangerous),"message":f"MCP tool '{name}' имеет excessive agency"})
 findings.sort(key=lambda x:(x["code"],x["tool"]))
 return findings,{"tools":len(tools),"flows":len(edges),"cycles_supported":True,"roots":sorted(n for n,c in incoming.items() if c==0)}
def sarif(findings,path):
 rules=[{"id":code,"name":code} for code in sorted({i["code"] for i in findings})];results=[{"ruleId":i["code"],"level":i["severity"],"message":{"text":i["message"]},"locations":[{"physicalLocation":{"artifactLocation":{"uri":Path(path).resolve().as_uri()},"region":{"startLine":1}}}]} for i in findings]
 return {"$schema":"https://json.schemastore.org/sarif-2.1.0.json","version":"2.1.0","runs":[{"tool":{"driver":{"name":"Yadro Guard MCP","version":"2.1.0","rules":rules}},"results":results}]}
def run(argv=None,stdout=sys.stdout,stderr=sys.stderr):
 p=argparse.ArgumentParser(prog="yadro-guard mcp");p.add_argument("command",choices=("scan",));p.add_argument("manifest");p.add_argument("--format",choices=("text","json","sarif"),default="text");p.add_argument("--quiet",action="store_true");args=p.parse_args(argv)
 try:findings,summary=analyze(*load(args.manifest))
 except (OSError,UnicodeError,json.JSONDecodeError,ManifestError) as error:print(f"неверный MCP manifest: {error}",file=stderr);return EXIT_SOURCE
 except Exception as error:print(f"внутренняя ошибка MCP scanner: {error}",file=stderr);return EXIT_INTERNAL
 if not args.quiet:
  if args.format=="json":print(json.dumps({"findings":findings,"summary":summary},ensure_ascii=False,indent=2),file=stdout)
  elif args.format=="sarif":print(json.dumps(sarif(findings,args.manifest),ensure_ascii=False,indent=2),file=stdout)
  else:
   for i in findings:print(f'{i["code"]}: {i["message"]}',file=stdout)
   if not findings:print("MCP tool graph соответствует политике",file=stdout)
 return EXIT_POLICY if findings else EXIT_OK
def main():raise SystemExit(run())
if __name__=="__main__":main()
