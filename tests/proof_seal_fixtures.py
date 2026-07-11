from src.proof_seal import *
ZERO="0"*64
ONE="1"*64
def minimal_core():
 compiler=CompilerIdentity("yadro-guard","2.1.0","ru","1.0")
 subject=SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,ZERO,ZERO,ZERO,ZERO,"x86_64-unknown-linux-gnu","elf-object")
 return ProofSealCore(compiler,subject,make_analysis())
def rich_core(order=False):
 assumption=make_assumption("yadro_ext_v1_send","i64(i64)","ДоступСети","identity",False,"call",True)
 span=SourceSpan("src/пример.яд",1,4,0);cid=call_site_id("ru",module_id("ru",b"source"),"caller","callee","Вызов",1,4,0)
 values=("ПДн","Здоровье") if order else ("Здоровье","ПДн")
 call=make_call_site(cid,"caller","callee",span,required_capabilities=("ДоступСети",),incoming_labels=values,assumption_ids=(assumption.id,),reachable_entries=("entry",))
 compiler=CompilerIdentity("yadro-guard","2.1.0","ru","1.0")
 subject=SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,ZERO,ONE,ZERO,ONE,"x86_64-pc-windows-msvc","coff-object")
 return ProofSealCore(compiler,subject,make_analysis(("entry",),(call,),(assumption,),FixpointEvidence("bounded-monotone-1.0",values,1,5)))
