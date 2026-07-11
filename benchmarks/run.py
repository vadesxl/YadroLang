import io,json,platform,statistics,tempfile,time
from pathlib import Path
from src.main import компилировать
from src.лексер import Лексер
from src.синтаксис import Парсер
from src.этика import ЭтическийАнализатор
from src.mcp_guard import run as run_mcp
from src.proof_seal import CompilerIdentity,SubjectBinding,ProofSealCore,SourceSpan,FixpointEvidence,POLICY_VERSION,LLVM_NORMALIZATION_VERSION,make_assumption,make_call_site,make_analysis,module_id,seal,canonical_bytes
from src.proof_seal_verify import inspect_bytes,verify_bytes
ИСТОЧНИК='''функ помощь(х) { если х > 2 { вернуть х * 2 } иначе { вернуть х + 1 } } функ старт() { пусть н = 7 пока н < 9 { н = н + 1 } вернуть помощь(н) }'''
ЭТИКА='''функ помощь(х) { вернуть х + 1 } функ старт() { пусть п = пользователь.данные() пусть ч = анонимизировать(п) вернуть помощь(ч) }'''
MCP={"version":"1.0","tools":[{"name":"crm.читать","labels":["ПДн"]},{"name":"privacy.редактировать","sanitizes":["ПДн"]},{"name":"сеть.отправить","capabilities":["ДоступСети"]}],"flows":[["crm.читать","privacy.редактировать"],["privacy.редактировать","сеть.отправить"]]}
def measure(fn,rounds):
 values=[]
 for _ in range(rounds):
  start=time.perf_counter_ns();fn();values.append((time.perf_counter_ns()-start)/1_000_000)
 return {"median_ms":round(statistics.median(values),4),"p95_ms":round(sorted(values)[int(len(values)*.95)-1],4),"rounds":rounds}
def analyze():ЭтическийАнализатор().проверить(Парсер(Лексер(ЭТИКА).токены()).разобрать())
def mcp():
 path=Path(tempfile.gettempdir())/'yadro-benchmark-mcp-ru.json';path.write_text(json.dumps(MCP,ensure_ascii=False));run_mcp(['scan',str(path)],io.StringIO(),io.StringIO())
ZERO="0"*64
assumptions=tuple(make_assumption(f"ext{i}","i64(i64)","ДоступСети","identity",False,"call",True) for i in range(8))
module=module_id("ru",b"benchmark-source");calls=[]
for index in range(32):
 assumption=assumptions[index%len(assumptions)];span=SourceSpan("benchmark/input.яд",index,index+1,index)
 calls.append(make_call_site("ru",module,"call","caller",f"callee{index}",span,required_capabilities=("ДоступСети",),incoming_labels=("ПДн",),assumption_ids=(assumption.id,),reachable_entries=("entry",)))
analysis=make_analysis(("entry",),calls,assumptions,FixpointEvidence("bounded-monotone-1.0",("ПДн",),8,64))
core=ProofSealCore(CompilerIdentity("yadro-guard","2.1.0","ru","1.0"),SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,ZERO,ZERO,ZERO,ZERO,"x86_64-unknown-linux-gnu","elf-object"),analysis)
PROOF=canonical_bytes(seal(core));META={"payload_bytes":len(PROOF),"call_site_count":len(calls),"assumption_count":len(assumptions)}
def metric(fn,rounds=120):
 result=measure(fn,rounds);result.update(META);return result
result={"schema":"yadro-benchmark-1.0","python":platform.python_version(),"platform":platform.platform(),"compile":measure(lambda:компилировать(ИСТОЧНИК),40),"compile_checked":measure(lambda:компилировать(ИСТОЧНИК,арифметика="checked"),40),"ethical_analysis":measure(analyze,80),"mcp_scan":measure(mcp,120),"proof_seal_serialize":metric(lambda:canonical_bytes(seal(core))),"proof_seal_parse":metric(lambda:inspect_bytes(PROOF)),"proof_seal_verify":metric(lambda:verify_bytes(PROOF))}
print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
