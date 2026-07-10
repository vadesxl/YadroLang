# -*- coding: utf-8 -*-
"""Static MCP manifest and tool-graph scanner for Yadro Guard."""
import argparse
import json
import sys
from pathlib import Path

EXIT_OK, EXIT_POLICY, EXIT_SOURCE = 0, 2, 3
SENSITIVE = {"ПДн", "Финансы", "Здоровье", "УчетныеДанные", "Локация"}
DANGEROUS_CAPABILITIES = {"ДоступСети", "ЗаписьДиска", "ЗаписьБД", "ВыполнениеИнструмента", "ДоступСекретов"}


class ManifestError(ValueError): pass


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != "1.0" or not isinstance(data.get("tools"), list): raise ManifestError("нужны version '1.0' и tools")
    tools = {}
    for tool in data["tools"]:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"]: raise ManifestError("у каждого tool должно быть имя")
        if tool["name"] in tools: raise ManifestError(f"повторный tool: {tool['name']}")
        labels, sanitizes, capabilities = set(tool.get("labels", [])), set(tool.get("sanitizes", [])), set(tool.get("capabilities", []))
        if not labels <= SENSITIVE or not sanitizes <= SENSITIVE: raise ManifestError(f"неизвестная метка: {tool['name']}")
        tools[tool["name"]] = {"labels":labels, "sanitizes":sanitizes, "capabilities":capabilities}
    edges = []
    for flow in data.get("flows", []):
        if not isinstance(flow, list) or len(flow) != 2 or flow[0] not in tools or flow[1] not in tools: raise ManifestError(f"неверное ребро: {flow!r}")
        edges.append((flow[0],flow[1]))
    return tools, edges


def scan(tools, edges):
    state = {name:set(tool["labels"]) for name,tool in tools.items()}; changed = True
    while changed:
        changed = False
        for source,target in edges:
            merged = state[target] | (state[source] - tools[target]["sanitizes"])
            if merged != state[target]: state[target] = merged; changed = True
    findings = []
    for name,tool in tools.items():
        dangerous = tool["capabilities"] & DANGEROUS_CAPABILITIES
        if state[name] and dangerous: findings.append({"code":"ЯДРО-MCP-2301","tool":name,"labels":sorted(state[name]),"capabilities":sorted(dangerous),"message":f"Чувствительные данные достигают MCP tool '{name}'"})
        if len(dangerous) >= 3: findings.append({"code":"ЯДРО-MCP-2401","tool":name,"capabilities":sorted(dangerous),"message":f"MCP tool '{name}' имеет excessive agency"})
    return findings


def sarif(findings,path):
    rules=[{"id":i["code"],"name":i["code"]} for i in {i["code"]:i for i in findings}.values()]
    results=[{"ruleId":i["code"],"level":"error","message":{"text":i["message"]},"locations":[{"physicalLocation":{"artifactLocation":{"uri":str(path)},"region":{"startLine":1}}}]} for i in findings]
    return {"$schema":"https://json.schemastore.org/sarif-2.1.0.json","version":"2.1.0","runs":[{"tool":{"driver":{"name":"Yadro Guard MCP","version":"2.1.0-dev","rules":rules}},"results":results}]}


def run(argv=None,stdout=sys.stdout,stderr=sys.stderr):
    parser=argparse.ArgumentParser(prog="yadro-guard-mcp"); parser.add_argument("command",choices=("scan",)); parser.add_argument("manifest"); parser.add_argument("--format",choices=("text","json","sarif"),default="text"); args=parser.parse_args(argv)
    try: findings=scan(*load(args.manifest))
    except (OSError,UnicodeError,json.JSONDecodeError,ManifestError) as error: print(f"неверный MCP manifest: {error}",file=stderr); return EXIT_SOURCE
    if args.format=="json": print(json.dumps({"findings":findings},ensure_ascii=False,indent=2),file=stdout)
    elif args.format=="sarif": print(json.dumps(sarif(findings,args.manifest),ensure_ascii=False,indent=2),file=stdout)
    else:
        for item in findings: print(f'{item["code"]}: {item["message"]}',file=stdout)
        if not findings: print("MCP tool graph соответствует политике",file=stdout)
    return EXIT_POLICY if findings else EXIT_OK


def main(): raise SystemExit(run())
if __name__=="__main__": main()
