import hashlib,unittest
from src.proof_seal import *
class ProofSealIdTests(unittest.TestCase):
 def test_module_id_vector(self):
  expected=hashlib.sha256(b"YADRO-MODULE\0ru\0abc").hexdigest();self.assertEqual(expected,module_id("ru",b"abc"))
 def test_call_site_id_vector(self):
  module=module_id("ru",b"abc");parts=("ru",module,"caller","callee","Call","1","2","3");expected=hashlib.sha256(b"YADRO-CALL-SITE\0"+b"\0".join(x.encode() for x in parts)).hexdigest();self.assertEqual(expected,call_site_id("ru",module,"caller","callee","Call",1,2,3))
 def test_call_site_safe_integer_max(self):
  value=call_site_id("ru",module_id("ru",b"x"),"a","b","Call",MAX_SAFE_INTEGER,MAX_SAFE_INTEGER,MAX_SAFE_INTEGER);self.assertRegex(value,r"^[0-9a-f]{64}$")
  for invalid in (MAX_SAFE_INTEGER+1,True,1.0,-1):
   with self.subTest(value=invalid),self.assertRaises(ProofSealError):call_site_id("ru",module_id("ru",b"x"),"a","b","Call",invalid,MAX_SAFE_INTEGER,0)
 def test_assumption_id_content_addressed(self):
  first=make_assumption("sym","i64()",None,"identity",False,"call",True);second=make_assumption("sym","i64()",None,"identity",False,"call",True);changed=make_assumption("sym","i64()",None,"identity",False,"call",False)
  self.assertEqual(first.id,second.id);self.assertNotEqual(first.id,changed.id)
 def test_bool_is_not_offset(self):
  with self.assertRaises(ProofSealError):call_site_id("ru",module_id("ru",b"x"),"a","b","Call",True,1,0)
if __name__=="__main__":unittest.main()
