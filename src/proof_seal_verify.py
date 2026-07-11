# -*- coding: utf-8 -*-
"""Phase 2: bounded, strict, offline verification of Yadro Proof Seal bytes."""
from dataclasses import dataclass
import hmac,json,unicodedata
from src.proof_seal import (MAX_SEAL_BYTES,MAX_CALL_SITES,MAX_ENTRY_POINTS,MAX_ASSUMPTIONS,MAX_SEMANTIC_SET,MAX_IDENTIFIER_BYTES,MAX_PATH_BYTES,MAX_SAFE_INTEGER,SCHEMA,POLICY_VERSION,LLVM_NORMALIZATION_VERSION,ProofSealError,TrustState,CompilerIdentity,SourceSpan,CallSiteEvidence,FixpointEvidence,AnalysisEvidence,SubjectBinding,ProofSealCore,ProofSeal,make_assumption,canonical_bytes,seal)
MAX_DEPTH=16
class ProofVerificationError(ValueError):
 code="ЯДРО-П0000"
 def __init__(self,message):self.message=message;super().__init__(f"[{self.code}] {message}")
class ProofReadError(ProofVerificationError):code="ЯДРО-П1001"
class ProofEncodingError(ProofVerificationError):code="ЯДРО-П1002"
class ProofDepthError(ProofVerificationError):code="ЯДРО-П1003"
class ProofDuplicateKeyError(ProofVerificationError):code="ЯДРО-П1004"
class ProofSyntaxError(ProofVerificationError):code="ЯДРО-П1005"
class ProofVersionError(ProofVerificationError):code="ЯДРО-П1101"
class ProofStructureError(ProofVerificationError):code="ЯДРО-П1201"
class ProofValueError(ProofVerificationError):code="ЯДРО-П1202"
class ProofOrderingError(ProofVerificationError):code="ЯДРО-П1203"
class ProofDigestError(ProofVerificationError):code="ЯДРО-П1301"
class ProofCanonicalError(ProofVerificationError):code="ЯДРО-П1302"
class ProofReferenceError(ProofVerificationError):code="ЯДРО-П1303"
@dataclass(frozen=True,slots=True)
class VerificationResult:
 valid:bool;verified:bool;schema:str;trust_mode:str;authenticity:str;diagnostic_code:str;message:str

def _decode(data):
 if not isinstance(data,bytes):raise ProofReadError("proof input must be bytes")
 if not data:raise ProofReadError("proof input is empty")
 if len(data)>MAX_SEAL_BYTES:raise ProofReadError("proof input exceeds size limit")
 if data.startswith(b"\xef\xbb\xbf"):raise ProofEncodingError("UTF-8 BOM is forbidden")
 try:return data.decode("utf-8")
 except UnicodeDecodeError as error:raise ProofEncodingError("proof input is not valid UTF-8") from error

def _scan_depth(text):
 depth=0;in_string=False;escaped=False
 for ch in text:
  if in_string:
   if escaped:escaped=False
   elif ch=="\\":escaped=True
   elif ch=='"':in_string=False
   elif ord(ch)<32:raise ProofDepthError("raw control character in JSON string")
  elif ch=='"':in_string=True
  elif ch in "{[":
   depth+=1
   if depth>MAX_DEPTH:raise ProofDepthError("JSON nesting exceeds limit")
  elif ch in "]}":
   depth-=1
   if depth<0:raise ProofSyntaxError("unbalanced JSON container")
 if in_string:raise ProofDepthError("unterminated JSON string")
 return depth

def _pairs(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ProofDuplicateKeyError("duplicate JSON object key")
  result[key]=value
 return result

def _json_integer(text):
 digits=text.lstrip("-")
 if len(digits)>16:raise ProofValueError("JSON integer exceeds safe range")
 try:value=int(text)
 except ValueError as error:raise ProofValueError("invalid JSON integer") from error
 if not 0<=value<=MAX_SAFE_INTEGER:raise ProofValueError("JSON integer exceeds safe range")
 return value
def _no_float(_):raise ProofValueError("floating-point JSON values are forbidden")

def _parse(data):
 text=_decode(data);_scan_depth(text)
 try:return json.loads(text,object_pairs_hook=_pairs,parse_int=_json_integer,parse_float=_no_float,parse_constant=_no_float)
 except ProofVerificationError:raise
 except (json.JSONDecodeError,ValueError) as error:raise ProofSyntaxError("invalid JSON syntax") from error

def _nfc(value,name,max_bytes=MAX_IDENTIFIER_BYTES,empty=False):
 if not isinstance(value,str):raise ProofValueError(f"{name} must be a string")
 if not empty and not value:raise ProofValueError(f"{name} must not be empty")
 if any(0xD800<=ord(ch)<=0xDFFF for ch in value):raise ProofValueError(f"{name} contains invalid Unicode scalar value")
 if unicodedata.normalize("NFC",value)!=value:raise ProofValueError(f"{name} must be NFC")
 try:encoded=value.encode("utf-8")
 except UnicodeEncodeError as error:raise ProofValueError(f"{name} contains invalid Unicode scalar value") from error
 if len(encoded)>max_bytes:raise ProofValueError(f"{name} exceeds byte limit")
 if "\x00" in value or any(ord(ch)<32 or ord(ch)==127 for ch in value):raise ProofValueError(f"{name} contains forbidden character")
 return value

def _obj(value,required,name):
 if not isinstance(value,dict):raise ProofStructureError(f"{name} must be an object")
 if set(value)!=set(required):raise ProofStructureError(f"{name} fields do not match schema")
 return value

def _integer(value,name,minimum=0):
 if not isinstance(value,int) or isinstance(value,bool) or not minimum<=value<=MAX_SAFE_INTEGER:raise ProofValueError(f"{name} must be an integer in {minimum}..{MAX_SAFE_INTEGER}")
 return value
def _boolean(value,name):
 if not isinstance(value,bool):raise ProofValueError(f"{name} must be boolean")
 return value
def _hash(value,name):
 value=_nfc(value,name,64)
 if len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value):raise ProofValueError(f"{name} must be lowercase SHA-256")
 return value

def _ordered_strings(value,name,max_items=MAX_SEMANTIC_SET,hashes=False):
 if not isinstance(value,list):raise ProofStructureError(f"{name} must be an array")
 if len(value)>max_items:raise ProofValueError(f"{name} exceeds item limit")
 checked=tuple(_hash(item,name) if hashes else _nfc(item,name) for item in value)
 if len(set(checked))!=len(checked) or tuple(sorted(checked,key=lambda x:x.encode("utf-8")))!=checked:raise ProofOrderingError(f"{name} must be unique and canonically sorted")
 return checked

def _preflight(root):
 if not isinstance(root,dict):raise ProofVersionError("proof root must be an object")
 try:
  schema=_nfc(root.get("schema"),"schema",64);subject=root.get("subject")
  if not isinstance(subject,dict):raise ProofVersionError("subject versions are missing")
  policy=_nfc(subject.get("policy_schema_version"),"policy schema version",64);llvm=_nfc(subject.get("llvm_normalization_version"),"LLVM normalization version",64)
 except ProofValueError as error:raise ProofVersionError("proof version fields are missing or invalid") from error
 if (schema,policy,llvm)!=(SCHEMA,POLICY_VERSION,LLVM_NORMALIZATION_VERSION):raise ProofVersionError("proof version tuple is unsupported")
 return schema

def _trust(value):
 value=_obj(value,("mode","authenticity"),"trust");mode=_nfc(value["mode"],"trust mode");auth=_nfc(value["authenticity"],"authenticity")
 if (mode,auth)!=("unsigned","not-provided"):raise ProofValueError("unsupported trust state")
 return TrustState(mode,auth)
def _compiler(value):
 value=_obj(value,("name","version","frontend","semantic_surface","evidence_algorithm","llvm_compatibility"),"compiler")
 try:return CompilerIdentity(value["name"],value["version"],value["frontend"],value["semantic_surface"],value["evidence_algorithm"],value["llvm_compatibility"])
 except ProofSealError as error:raise ProofValueError("invalid compiler identity") from error
def _subject(value):
 names=("policy_schema_version","llvm_normalization_version","source_sha256","policy_sha256","llvm_sha256","artifact_sha256","target_triple","artifact_kind");value=_obj(value,names,"subject")
 try:return SubjectBinding(*(value[name] for name in names))
 except ProofSealError as error:raise ProofValueError("invalid subject binding") from error
def _span(value):
 value=_obj(value,("module_path","start_byte","end_byte","ordinal"),"span")
 _nfc(value["module_path"],"module_path",MAX_PATH_BYTES);_integer(value["start_byte"],"start_byte");_integer(value["end_byte"],"end_byte");_integer(value["ordinal"],"ordinal")
 try:return SourceSpan(value["module_path"],value["start_byte"],value["end_byte"],value["ordinal"])
 except ProofSealError as error:raise ProofValueError("invalid source span") from error

def _assumption(value):
 names=("id","symbol","abi_signature","capability","taint_transform","trusted_sanitizer","lifetime","no_retain","implementation_sha256");value=_obj(value,names,"assumption")
 _hash(value["id"],"assumption id");_nfc(value["symbol"],"external symbol");_nfc(value["abi_signature"],"ABI signature",512)
 if value["capability"] is not None:_nfc(value["capability"],"capability")
 _nfc(value["taint_transform"],"taint transform",512);_boolean(value["trusted_sanitizer"],"trusted_sanitizer");_nfc(value["lifetime"],"lifetime",512);_boolean(value["no_retain"],"no_retain")
 if value["implementation_sha256"] is not None:_hash(value["implementation_sha256"],"implementation digest")
 try:computed=make_assumption(value["symbol"],value["abi_signature"],value["capability"],value["taint_transform"],value["trusted_sanitizer"],value["lifetime"],value["no_retain"],value["implementation_sha256"])
 except ProofSealError as error:raise ProofValueError("invalid assumption") from error
 if not hmac.compare_digest(value["id"],computed.id):raise ProofReferenceError("assumption content ID mismatch")
 return computed

def _call(value):
 names=("id","caller","callee","span","required_capabilities","declared_capabilities","incoming_labels","outgoing_labels","sanitizers","declassified_labels","policy_rules","implicit_labels","assumption_ids","reachable_entries","status");value=_obj(value,names,"call site")
 call_id=_hash(value["id"],"call-site id");caller=_nfc(value["caller"],"caller");callee=_nfc(value["callee"],"callee");span=_span(value["span"])
 sets={name:_ordered_strings(value[name],name,MAX_ENTRY_POINTS if name=="reachable_entries" else MAX_SEMANTIC_SET,hashes=name=="assumption_ids") for name in names[4:14]}
 if value["status"]!="allowed":raise ProofValueError("call-site status must be allowed")
 try:return CallSiteEvidence(call_id,caller,callee,span,sets["required_capabilities"],sets["declared_capabilities"],sets["incoming_labels"],sets["outgoing_labels"],sets["sanitizers"],sets["declassified_labels"],sets["policy_rules"],sets["implicit_labels"],sets["assumption_ids"],sets["reachable_entries"],"allowed")
 except ProofSealError as error:raise ProofValueError("invalid call-site evidence") from error

def _fixpoint(value):
 value=_obj(value,("algorithm","lattice_labels","updates","bound"),"fixpoint");labels=_ordered_strings(value["lattice_labels"],"lattice_labels");updates=_integer(value["updates"],"updates");bound=_integer(value["bound"],"bound",1)
 if value["algorithm"]!="bounded-monotone-1.0" or updates>bound:raise ProofValueError("invalid fixpoint evidence")
 return FixpointEvidence(value["algorithm"],labels,updates,bound)

def _analysis(value):
 value=_obj(value,("entry_points","call_sites","assumptions","fixpoint"),"analysis");entries=_ordered_strings(value["entry_points"],"entry_points",MAX_ENTRY_POINTS)
 if not isinstance(value["assumptions"],list) or len(value["assumptions"])>MAX_ASSUMPTIONS:raise ProofValueError("assumptions exceed bound")
 assumptions=tuple(_assumption(item) for item in value["assumptions"])
 if tuple(sorted(assumptions,key=lambda x:x.id))!=assumptions or len({x.id for x in assumptions})!=len(assumptions):raise ProofOrderingError("assumptions must be unique and sorted")
 if not isinstance(value["call_sites"],list) or len(value["call_sites"])>MAX_CALL_SITES:raise ProofValueError("call sites exceed bound")
 calls=tuple(_call(item) for item in value["call_sites"])
 if tuple(sorted(calls,key=lambda x:x.id))!=calls or len({x.id for x in calls})!=len(calls):raise ProofOrderingError("call sites must be unique and sorted")
 known={item.id for item in assumptions}
 if any(ref not in known for call in calls for ref in call.assumption_ids):raise ProofReferenceError("call site references unknown assumption")
 try:return AnalysisEvidence(entries,calls,assumptions,_fixpoint(value["fixpoint"]))
 except ProofSealError as error:raise ProofValueError("invalid analysis evidence") from error

def _reconstruct(root):
 root=_obj(root,("schema","trust","compiler","subject","analysis","seal_sha256"),"proof");_preflight(root);digest=_hash(root["seal_sha256"],"seal_sha256")
 return ProofSealCore(_compiler(root["compiler"]),_subject(root["subject"]),_analysis(root["analysis"]),_trust(root["trust"]),root["schema"]),digest

def _pipeline(data,verify):
 root=_parse(data);schema=_preflight(root);core,digest=_reconstruct(root)
 if verify:
  expected=seal(core).seal_sha256
  if not hmac.compare_digest(digest,expected):raise ProofDigestError("seal digest mismatch")
  try:proof=ProofSeal(core,digest)
  except ProofSealError as error:raise ProofDigestError("seal digest mismatch") from error
  if not hmac.compare_digest(canonical_bytes(proof),data):raise ProofCanonicalError("proof bytes are not canonical")
 return VerificationResult(True,verify,schema,core.trust.mode,core.trust.authenticity,"","verified consistency" if verify else "structure inspected")
def _public(data,verify):
 try:return _pipeline(data,verify)
 except ProofVerificationError as error:return VerificationResult(False,False,"","","",error.code,error.message)
 except UnicodeError:return VerificationResult(False,False,"","","",ProofValueError.code,"proof contains invalid Unicode scalar value")
def inspect_bytes(data):return _public(data,False)
def verify_bytes(data):return _public(data,True)
