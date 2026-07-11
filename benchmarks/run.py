import io,json,platform,statistics,tempfile,time
from pathlib import Path
from src.main import компилировать
from src.лексер import Лексер
from src.синтаксис import Парсер
from src.этика import ЭтическийАнализатор
from src.mcp_guard import run as run_mcp
from src.proof_seal import CompilerIdentity,SubjectBinding,ProofSealCore,POLICY_VERSION,LLVM_NORMALIZATION_VERSION,make_analysis,seal,canonical_bytes
ИСТОЧНИК='''функ помощь(х) { если х > 2 { вернуть х * 2 } иначе { вернуть х + 1 } } функ старт() { пусть н = 7 пока н < 9 { н = н + 1 } вернуть помощь(н) }'''
ЭТИКА='''функ помощь(х) { вернуть х + 1 } функ старт() { пусть п = пользователь.данные() пусть ч = анонимизировать(п) вернуть помощь(ч) }'''
MCP={"version":"1.0","tools":[{"name":"crm.читать","labels":["ПДн"]},{"name":"privacy.редактировать","sanitizes":["ПДн"]},{"name":"сеть.отправить","capabilities":["ДоступСети"]}],"flows":[["crm.читать","privacy.редактировать"],["privacy.редактировать","сеть.отправить"]]}
def measure(fn,rounds):
 значения=[]
 for _ in range(rounds):
  начало=time.perf_counter_ns();fn();значения.append((time.perf_counter_ns()-начало)/1_000_000)
 return {"median_ms":round(statistics.median(значения),4),"p95_ms":round(sorted(значения)[int(len(значения)*.95)-1],4),"rounds":rounds}
def analyze():ЭтическийАнализатор().проверить(Парсер(Лексер(ЭТИКА).токены()).разобрать())
def mcp():
 путь=Path(tempfile.gettempdir())/'yadro-benchmark-mcp-ru.json';путь.write_text(json.dumps(MCP,ensure_ascii=False));run_mcp(['scan',str(путь)],io.StringIO(),io.StringIO())
_ZERO="0"*64
_PROOF=seal(ProofSealCore(CompilerIdentity("yadro-guard","2.1.0","ru","1.0"),SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,_ZERO,_ZERO,_ZERO,_ZERO,"x86_64-unknown-linux-gnu","elf-object"),make_analysis()))
proof_metric=measure(lambda:canonical_bytes(_PROOF),120);proof_metric.update({"payload_bytes":len(canonical_bytes(_PROOF)),"call_site_count":0,"assumption_count":0})
результат={"schema":"yadro-benchmark-1.0","python":platform.python_version(),"platform":platform.platform(),"compile":measure(lambda:компилировать(ИСТОЧНИК),40),"ethical_analysis":measure(analyze,80),"mcp_scan":measure(mcp,120),"proof_seal_serialize":proof_metric}
print(json.dumps(результат,ensure_ascii=False,indent=2,sort_keys=True))
