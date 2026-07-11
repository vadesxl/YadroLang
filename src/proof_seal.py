# -*- coding: utf-8 -*-
"""Phase 1 Yadro Proof Seal: immutable evidence and canonical serialization."""
from dataclasses import dataclass,fields
import hashlib,json,re,unicodedata
from typing import Iterable
MAX_SEAL_BYTES=1_048_576;MAX_CALL_SITES=10_000;MAX_ENTRY_POINTS=256;MAX_ASSUMPTIONS=2_000;MAX_SEMANTIC_SET=32;MAX_IDENTIFIER_BYTES=256;MAX_PATH_BYTES=512;MAX_SAFE_INTEGER=9_007_199_254_740_991
SCHEMA="yadro-proof-seal-1.0";POLICY_VERSION="yadro-policy-1.0";LLVM_NORMALIZATION_VERSION="yadro-llvm-normalization-1.0";_HEX=re.compile(r"^[0-9a-f]{64}$")
class ProofSealError(ValueError):pass
def _text(value,name,max_bytes=MAX_IDENTIFIER_BYTES,empty=False):
 if not isinstance(value,str):raise ProofSealError(f"{name} must be a string")
 if unicodedata.normalize("NFC",value)!=value:raise ProofSealError(f"{name} must be NFC")
 if not empty and not value:raise ProofSealError(f"{name} must not be empty")
 if len(value.encode("utf-8"))>max_bytes:raise ProofSealError(f"{name} exceeds {max_bytes} UTF-8 bytes")
 if "\x00" in value:raise ProofSealError(f"{name} contains NUL")
 if any(ord(ch)<32 or ord(ch)==127 for ch in value):raise ProofSealError(f"{name} contains control characters")
 return value
def _integer(value,name):
 if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=MAX_SAFE_INTEGER:raise ProofSealError(f"{name} must be an integer in 0..{MAX_SAFE_INTEGER}")
 return value
def _digest(value,name):
 _text(value,name,64)
 if not _HEX.fullmatch(value):raise ProofSealError(f"{name} must be lowercase SHA-256")
 return value
def _enum(value,name,allowed):
 _text(value,name)
 if value not in allowed:raise ProofSealError(f"unsupported {name}: {value}")
 return value
def _sort_key(value):return value.encode("utf-8")
def _tuple(value,name):
 if isinstance(value,(str,bytes)) or value is None:raise ProofSealError(f"{name} must be an iterable, not scalar")
 try:return tuple(value)
 except TypeError as error:raise ProofSealError(f"{name} must be iterable") from error
def canonical_strings(values:Iterable[str],name,max_items=MAX_SEMANTIC_SET):
 raw=_tuple(values,name)
 if len(raw)>max_items:raise ProofSealError(f"too many {name}, maximum {max_items}")
 checked=tuple(_text(value,name) for value in raw)
 if len(set(checked))!=len(checked):raise ProofSealError(f"duplicate {name}")
 return tuple(sorted(checked,key=_sort_key))
def safe_path(value):
 value=_text(value,"module_path",MAX_PATH_BYTES)
 if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:",value) or value.startswith("//") or any(part in ("",".","..") for part in value.split("/")):raise ProofSealError("unsafe module_path")
 return value
def _canonical_mapping(mapping):
 try:text=json.dumps(mapping,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
 except (TypeError,ValueError) as error:raise ProofSealError(f"cannot canonicalize: {error}") from error
 data=(text+"\n").encode("utf-8")
 if len(data)>MAX_SEAL_BYTES:raise ProofSealError("proof exceeds maximum size")
 return data
def _assumption_payload(symbol,abi_signature,capability,taint_transform,trusted_sanitizer,lifetime,no_retain,implementation_sha256):return {"abi_signature":abi_signature,"capability":capability,"implementation_sha256":implementation_sha256,"lifetime":lifetime,"no_retain":no_retain,"symbol":symbol,"taint_transform":taint_transform,"trusted_sanitizer":trusted_sanitizer}
def _assumption_digest_fields(**payload):return hashlib.sha256(b"YADRO-ASSUMPTION\0"+_canonical_mapping(payload)).hexdigest()
@dataclass(frozen=True,slots=True)
class TrustState:
 mode:str="unsigned";authenticity:str="not-provided"
 def __post_init__(self):_enum(self.mode,"trust mode",{"unsigned"});_enum(self.authenticity,"authenticity",{"not-provided"})
@dataclass(frozen=True,slots=True)
class CompilerIdentity:
 name:str;version:str;frontend:str;semantic_surface:str;evidence_algorithm:str="yadro-evidence-1.0";llvm_compatibility:str="llvmlite-0.43"
 def __post_init__(self):
  if self.name!="yadro-guard":raise ProofSealError("unsupported compiler")
  _text(self.version,"compiler version",64);_enum(self.frontend,"frontend",{"ru","en"});_text(self.semantic_surface,"semantic surface",32)
  if self.evidence_algorithm!="yadro-evidence-1.0":raise ProofSealError("unsupported evidence algorithm")
  _text(self.llvm_compatibility,"LLVM compatibility",64)
@dataclass(frozen=True,slots=True)
class SourceSpan:
 module_path:str;start_byte:int;end_byte:int;ordinal:int
 def __post_init__(self):
  safe_path(self.module_path);_integer(self.start_byte,"start_byte");_integer(self.end_byte,"end_byte");_integer(self.ordinal,"ordinal")
  if self.end_byte<self.start_byte:raise ProofSealError("end_byte precedes start_byte")
@dataclass(frozen=True,slots=True)
class ExternalAssumption:
 id:str;symbol:str;abi_signature:str;capability:str|None;taint_transform:str;trusted_sanitizer:bool;lifetime:str;no_retain:bool;implementation_sha256:str|None
 def __post_init__(self):
  _digest(self.id,"assumption id");_text(self.symbol,"external symbol");_text(self.abi_signature,"ABI signature",512)
  if self.capability is not None:_text(self.capability,"capability")
  _text(self.taint_transform,"taint transform",512);_text(self.lifetime,"lifetime",512)
  if not isinstance(self.trusted_sanitizer,bool) or not isinstance(self.no_retain,bool):raise ProofSealError("assumption flags must be bool")
  if self.implementation_sha256 is not None:_digest(self.implementation_sha256,"implementation digest")
  expected=_assumption_digest_fields(**_assumption_payload(self.symbol,self.abi_signature,self.capability,self.taint_transform,self.trusted_sanitizer,self.lifetime,self.no_retain,self.implementation_sha256))
  if self.id!=expected:raise ProofSealError("assumption id does not match content")
@dataclass(frozen=True,slots=True)
class CallSiteEvidence:
 id:str;caller:str;callee:str;span:SourceSpan;required_capabilities:tuple[str,...];declared_capabilities:tuple[str,...];incoming_labels:tuple[str,...];outgoing_labels:tuple[str,...];sanitizers:tuple[str,...];declassified_labels:tuple[str,...];policy_rules:tuple[str,...];implicit_labels:tuple[str,...];assumption_ids:tuple[str,...];reachable_entries:tuple[str,...];status:str="allowed"
 def __post_init__(self):
  _digest(self.id,"call-site id");_text(self.caller,"caller");_text(self.callee,"callee")
  if not isinstance(self.span,SourceSpan):raise ProofSealError("span must be SourceSpan")
  for name in ("required_capabilities","declared_capabilities","incoming_labels","outgoing_labels","sanitizers","declassified_labels","policy_rules","implicit_labels","reachable_entries"):_require_canonical_strings(getattr(self,name),name,MAX_ENTRY_POINTS if name=="reachable_entries" else MAX_SEMANTIC_SET)
  _require_digests(self.assumption_ids,"assumption_ids")
  if self.status!="allowed":raise ProofSealError("successful evidence status must be allowed")
@dataclass(frozen=True,slots=True)
class FixpointEvidence:
 algorithm:str;lattice_labels:tuple[str,...];updates:int;bound:int
 def __post_init__(self):
  if self.algorithm!="bounded-monotone-1.0":raise ProofSealError("unsupported fixpoint algorithm")
  _require_canonical_strings(self.lattice_labels,"lattice_labels");_integer(self.updates,"updates");_integer(self.bound,"bound")
  if self.bound<1 or self.updates>self.bound:raise ProofSealError("invalid fixpoint bound")
@dataclass(frozen=True,slots=True)
class AnalysisEvidence:
 entry_points:tuple[str,...];call_sites:tuple[CallSiteEvidence,...];assumptions:tuple[ExternalAssumption,...];fixpoint:FixpointEvidence
 def __post_init__(self):
  _require_canonical_strings(self.entry_points,"entry_points",MAX_ENTRY_POINTS)
  if not isinstance(self.call_sites,tuple) or not isinstance(self.assumptions,tuple):raise ProofSealError("evidence collections must be tuples")
  if len(self.call_sites)>MAX_CALL_SITES or len(self.assumptions)>MAX_ASSUMPTIONS:raise ProofSealError("evidence collection exceeds bound")
  if not all(isinstance(x,CallSiteEvidence) for x in self.call_sites) or tuple(sorted(self.call_sites,key=lambda x:x.id))!=self.call_sites:raise ProofSealError("call_sites must be typed and sorted")
  if not all(isinstance(x,ExternalAssumption) for x in self.assumptions) or tuple(sorted(self.assumptions,key=lambda x:x.id))!=self.assumptions:raise ProofSealError("assumptions must be typed and sorted")
  if len({x.id for x in self.call_sites})!=len(self.call_sites) or len({x.id for x in self.assumptions})!=len(self.assumptions):raise ProofSealError("duplicate evidence id")
  if not isinstance(self.fixpoint,FixpointEvidence):raise ProofSealError("fixpoint must be FixpointEvidence")
@dataclass(frozen=True,slots=True)
class SubjectBinding:
 policy_schema_version:str;llvm_normalization_version:str;source_sha256:str;policy_sha256:str;llvm_sha256:str;artifact_sha256:str;target_triple:str;artifact_kind:str
 def __post_init__(self):
  if self.policy_schema_version!=POLICY_VERSION:raise ProofSealError("unsupported policy schema")
  if self.llvm_normalization_version!=LLVM_NORMALIZATION_VERSION:raise ProofSealError("unsupported LLVM normalization")
  for name in ("source_sha256","policy_sha256","llvm_sha256","artifact_sha256"):_digest(getattr(self,name),name)
  _text(self.target_triple,"target triple",128);_enum(self.artifact_kind,"artifact kind",{"elf-object","macho-object","coff-object"})
@dataclass(frozen=True,slots=True)
class ProofSealCore:
 compiler:CompilerIdentity;subject:SubjectBinding;analysis:AnalysisEvidence;trust:TrustState=TrustState();schema:str=SCHEMA
 def __post_init__(self):
  if self.schema!=SCHEMA:raise ProofSealError("unsupported proof schema")
  if not isinstance(self.trust,TrustState) or not isinstance(self.compiler,CompilerIdentity) or not isinstance(self.subject,SubjectBinding) or not isinstance(self.analysis,AnalysisEvidence):raise ProofSealError("invalid proof core types")
@dataclass(frozen=True,slots=True)
class ProofSeal:
 core:ProofSealCore;seal_sha256:str
 def __post_init__(self):
  if not isinstance(self.core,ProofSealCore):raise ProofSealError("core must be ProofSealCore")
  _digest(self.seal_sha256,"seal_sha256")
  if self.seal_sha256!=_seal_digest(self.core):raise ProofSealError("seal digest does not match core")
def _require_canonical_strings(value,name,max_items=MAX_SEMANTIC_SET):
 if not isinstance(value,tuple) or canonical_strings(value,name,max_items)!=value:raise ProofSealError(f"{name} must be canonical tuple")
def _require_digests(value,name):
 if not isinstance(value,tuple) or len(value)>MAX_SEMANTIC_SET:raise ProofSealError(f"invalid {name}")
 for item in value:_digest(item,name)
 if len(set(value))!=len(value) or tuple(sorted(value))!=value:raise ProofSealError(f"{name} must be unique and sorted")
def _plain(value):
 if isinstance(value,tuple):return [_plain(x) for x in value]
 if hasattr(value,"__dataclass_fields__"):return {field.name:_plain(getattr(value,field.name)) for field in fields(value)}
 if value is None or isinstance(value,(str,bool,int)):return value
 raise ProofSealError(f"unsupported canonical value: {type(value).__name__}")
def _core_mapping(core):return {"analysis":_plain(core.analysis),"compiler":_plain(core.compiler),"schema":core.schema,"subject":_plain(core.subject),"trust":_plain(core.trust)}
def _seal_digest(core):return hashlib.sha256(b"YADRO-PROOF-SEAL\0"+b"1.0\0"+_canonical_mapping(_core_mapping(core))).hexdigest()
def make_assumption(symbol,abi_signature,capability,taint_transform,trusted_sanitizer,lifetime,no_retain,implementation_sha256=None):
 payload=_assumption_payload(_text(symbol,"symbol"),_text(abi_signature,"ABI signature",512),None if capability is None else _text(capability,"capability"),_text(taint_transform,"taint transform",512),trusted_sanitizer,_text(lifetime,"lifetime",512),no_retain,None if implementation_sha256 is None else _digest(implementation_sha256,"implementation digest"))
 if not isinstance(trusted_sanitizer,bool) or not isinstance(no_retain,bool):raise ProofSealError("assumption flags must be bool")
 return ExternalAssumption(_assumption_digest_fields(**payload),**payload)
def make_call_site(id,caller,callee,span,**sets):
 names=("required_capabilities","declared_capabilities","incoming_labels","outgoing_labels","sanitizers","declassified_labels","policy_rules","implicit_labels","reachable_entries")
 values={name:canonical_strings(sets.get(name,()),name,MAX_ENTRY_POINTS if name=="reachable_entries" else MAX_SEMANTIC_SET) for name in names};assumption_ids=_tuple(sets.get("assumption_ids",()),"assumption_ids")
 for item in assumption_ids:_digest(item,"assumption id")
 if len(set(assumption_ids))!=len(assumption_ids):raise ProofSealError("duplicate assumption id")
 values["assumption_ids"]=tuple(sorted(assumption_ids));return CallSiteEvidence(id,caller,callee,span,**values)
def make_analysis(entry_points=(),call_sites=(),assumptions=(),fixpoint=None):
 calls=_tuple(call_sites,"call_sites");assumps=_tuple(assumptions,"assumptions")
 if not all(isinstance(x,CallSiteEvidence) for x in calls):raise ProofSealError("call_sites must contain CallSiteEvidence")
 if not all(isinstance(x,ExternalAssumption) for x in assumps):raise ProofSealError("assumptions must contain ExternalAssumption")
 if len({x.id for x in calls})!=len(calls) or len({x.id for x in assumps})!=len(assumps):raise ProofSealError("duplicate evidence id")
 return AnalysisEvidence(canonical_strings(entry_points,"entry_points",MAX_ENTRY_POINTS),tuple(sorted(calls,key=lambda x:x.id)),tuple(sorted(assumps,key=lambda x:x.id)),fixpoint or FixpointEvidence("bounded-monotone-1.0",(),0,1))
def module_id(frontend,source_bytes):
 frontend=_enum(frontend,"frontend",{"ru","en"})
 if not isinstance(source_bytes,bytes):raise ProofSealError("source must be bytes")
 return hashlib.sha256(b"YADRO-MODULE\0"+frontend.encode()+b"\0"+source_bytes).hexdigest()
def call_site_id(frontend,module_digest,caller,callee,ast_kind,start_byte,end_byte,ordinal):
 frontend=_enum(frontend,"frontend",{"ru","en"});_digest(module_digest,"module id");caller=_text(caller,"caller");callee=_text(callee,"callee");ast_kind=_text(ast_kind,"AST kind");start=_integer(start_byte,"start_byte");end=_integer(end_byte,"end_byte");order=_integer(ordinal,"ordinal")
 if end<start:raise ProofSealError("end_byte precedes start_byte")
 return hashlib.sha256(b"YADRO-CALL-SITE\0"+b"\0".join(x.encode() for x in (frontend,module_digest,caller,callee,ast_kind,str(start),str(end),str(order)))).hexdigest()
def canonical_bytes(value):
 if isinstance(value,ProofSealCore):return _canonical_mapping(_core_mapping(value))
 if isinstance(value,ProofSeal):
  mapping=_core_mapping(value.core);mapping["seal_sha256"]=value.seal_sha256;return _canonical_mapping(mapping)
 raise ProofSealError("serializer accepts only ProofSealCore or ProofSeal")
def seal(core):
 if not isinstance(core,ProofSealCore):raise ProofSealError("seal requires ProofSealCore")
 return ProofSeal(core,_seal_digest(core))
