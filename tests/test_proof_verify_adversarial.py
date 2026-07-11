import hashlib,json,random,unittest
from src.proof_seal import call_site_id
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import valid_bytes,parsed

def escaped(value):return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")
def utf8(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
def reseal(value):
 core={key:item for key,item in value.items() if key!="seal_sha256"};payload=utf8(core);value["seal_sha256"]=hashlib.sha256(b"YADRO-PROOF-SEAL\0"+b"1.0\0"+payload).hexdigest();return utf8(value)
def refresh_call_id(value):
 call=value["analysis"]["call_sites"][0];span=call["span"];call["id"]=call_site_id(value["compiler"]["frontend"],call["module_id"],call["caller"],call["callee"],call["semantic_kind"],span["start_byte"],span["end_byte"],span["ordinal"])

class ProofVerifyAdversarialTests(unittest.TestCase):
 def test_deterministic_mutation_corpus(self):
  original=valid_bytes();rng=random.Random(731);cases=[original[:i] for i in sorted(set((1,2,8,32,len(original)//2,len(original)-1)))]
  for _ in range(40):
   data=bytearray(original);index=rng.randrange(len(data));data[index]=rng.choice(b'{}[]"\\0123456789abcdef');cases.append(bytes(data))
  for data in cases:
   first=verify_bytes(data);second=verify_bytes(data);self.assertEqual((first.valid,first.diagnostic_code,first.message),(second.valid,second.diagnostic_code,second.message))
 def test_top_level_duplicate(self):
  data=b'{"schema":"x",'+valid_bytes()[1:];self.assertEqual(ProofDuplicateKeyError.code,inspect_bytes(data).diagnostic_code)
 def test_no_payload_echo(self):
  secret=b'SUPER_SECRET_DO_NOT_ECHO';result=inspect_bytes(b'{"schema":"'+secret+b'"}');self.assertNotIn("SUPER_SECRET",result.message)
 def test_forged_call_site_id_with_resealed_outer_digest_is_rejected(self):
  value=parsed();value["analysis"]["call_sites"][0]["id"]="f"*64;data=reseal(value)
  for check in (inspect_bytes,verify_bytes):
   result=check(data);self.assertFalse(result.valid);self.assertEqual(ProofReferenceError.code,result.diagnostic_code);self.assertEqual("call-site content ID mismatch",result.message);self.assertNotIn("ffff",result.message)
 def test_every_serialized_identity_mutation_is_detected(self):
  mutations=(lambda value:value["analysis"]["call_sites"][0].__setitem__("caller","changed"),lambda value:value["analysis"]["call_sites"][0].__setitem__("callee","changed"),lambda value:value["analysis"]["call_sites"][0].__setitem__("module_id","f"*64),lambda value:value["compiler"].__setitem__("frontend","en"),lambda value:value["analysis"]["call_sites"][0]["span"].__setitem__("start_byte",0),lambda value:value["analysis"]["call_sites"][0]["span"].__setitem__("end_byte",5),lambda value:value["analysis"]["call_sites"][0]["span"].__setitem__("ordinal",1))
  for mutate in mutations:
   value=parsed();mutate(value);result=inspect_bytes(reseal(value));self.assertFalse(result.valid);self.assertEqual(ProofReferenceError.code,result.diagnostic_code)
 def test_unknown_or_missing_identity_fields_fail_closed(self):
  value=parsed();value["analysis"]["call_sites"][0]["semantic_kind"]="вызов";self.assertEqual(ProofValueError.code,inspect_bytes(reseal(value)).diagnostic_code)
  for field in ("module_id","semantic_kind"):
   value=parsed();del value["analysis"]["call_sites"][0][field];self.assertEqual(ProofStructureError.code,inspect_bytes(reseal(value)).diagnostic_code)
 def test_lone_and_reversed_surrogates_are_controlled(self):
  for bad in ("\ud800","\udfff","\udfff\ud800"):
   cases=[]
   value=parsed();value["analysis"]["call_sites"][0]["caller"]=bad;cases.append(value)
   value=parsed();value["analysis"]["call_sites"][0]["callee"]=bad;cases.append(value)
   value=parsed();value["analysis"]["call_sites"][0]["span"]["module_path"]=bad;cases.append(value)
   value=parsed();value["analysis"]["assumptions"][0]["symbol"]=bad;cases.append(value)
   value=parsed();value["analysis"]["call_sites"][0]["incoming_labels"]=[bad];cases.append(value)
   for case in cases:
    with self.subTest(codepoints=[hex(ord(ch)) for ch in bad]):
     first=inspect_bytes(escaped(case));second=inspect_bytes(escaped(case));self.assertFalse(first.valid);self.assertEqual(ProofValueError.code,first.diagnostic_code);self.assertEqual((first.valid,first.diagnostic_code,first.message),(second.valid,second.diagnostic_code,second.message));self.assertNotIn("surrogate",first.message.lower())
 def test_surrogate_in_version_preflight_is_version_error(self):
  for bad in ("\ud800","\udfff","\udfff\ud800"):
   value=parsed();value["schema"]=bad;result=inspect_bytes(escaped(value));self.assertFalse(result.valid);self.assertEqual(ProofVersionError.code,result.diagnostic_code)
 def test_valid_non_bmp_scalar_is_accepted(self):
  for text in ("caller-🚀","caller-𐐷"):
   value=parsed();value["analysis"]["call_sites"][0]["caller"]=text;refresh_call_id(value);self.assertTrue(inspect_bytes(reseal(value)).valid)
if __name__=="__main__":unittest.main()
