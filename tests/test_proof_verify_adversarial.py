import json,random,unittest
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import valid_bytes,parsed

def escaped(value):
 return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")

class ProofVerifyAdversarialTests(unittest.TestCase):
 def test_deterministic_mutation_corpus(self):
  original=valid_bytes();rng=random.Random(731)
  cases=[original[:i] for i in sorted(set((1,2,8,32,len(original)//2,len(original)-1)))]
  for _ in range(40):
   data=bytearray(original);index=rng.randrange(len(data));data[index]=rng.choice(b'{}[]"\\0123456789abcdef');cases.append(bytes(data))
  for data in cases:
   first=verify_bytes(data);second=verify_bytes(data);self.assertEqual((first.valid,first.diagnostic_code,first.message),(second.valid,second.diagnostic_code,second.message))
 def test_top_level_duplicate(self):
  data=b'{"schema":"x",'+valid_bytes()[1:];self.assertEqual(ProofDuplicateKeyError.code,inspect_bytes(data).diagnostic_code)
 def test_no_payload_echo(self):
  secret=b'SUPER_SECRET_DO_NOT_ECHO';result=inspect_bytes(b'{"schema":"'+secret+b'"}');self.assertNotIn("SUPER_SECRET",result.message)
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
     first=inspect_bytes(escaped(case));second=inspect_bytes(escaped(case))
     self.assertFalse(first.valid);self.assertEqual(ProofValueError.code,first.diagnostic_code)
     self.assertEqual((first.valid,first.diagnostic_code,first.message),(second.valid,second.diagnostic_code,second.message))
     self.assertNotIn("surrogate",first.message.lower())
 def test_surrogate_in_version_preflight_is_version_error(self):
  for bad in ("\ud800","\udfff","\udfff\ud800"):
   value=parsed();value["schema"]=bad
   result=inspect_bytes(escaped(value));self.assertFalse(result.valid);self.assertEqual(ProofVersionError.code,result.diagnostic_code)
 def test_valid_non_bmp_scalar_is_accepted(self):
  for text in ("caller-🚀","caller-𐐷"):
   value=parsed();value["analysis"]["call_sites"][0]["caller"]=text
   self.assertTrue(inspect_bytes(escaped(value)).valid)
if __name__=="__main__":unittest.main()
