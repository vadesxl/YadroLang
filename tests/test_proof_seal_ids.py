import hashlib,unittest
from src.proof_seal import *
class ProofSealIdTests(unittest.TestCase):
 def test_module_id_vector(self):
  expected=hashlib.sha256(b"YADRO-MODULE\0ru\0abc").hexdigest();self.assertEqual(expected,module_id("ru",b"abc"))
 def test_call_site_id_vector(self):
  module=module_id("ru",b"abc");parts=("ru",module,"caller","callee","call","1","2","3");expected=hashlib.sha256(b"YADRO-CALL-SITE\0"+b"\0".join(x.encode() for x in parts)).hexdigest();self.assertEqual(expected,call_site_id("ru",module,"caller","callee","call",1,2,3))
 def test_every_identity_input_matters(self):
  module=module_id("ru",b"abc");base=call_site_id("ru",module,"caller","callee","call",1,2,3)
  variants=(call_site_id("en",module,"caller","callee","call",1,2,3),call_site_id("ru",module_id("ru",b"def"),"caller","callee","call",1,2,3),call_site_id("ru",module,"caller2","callee","call",1,2,3),call_site_id("ru",module,"caller","callee2","call",1,2,3),call_site_id("ru",module,"caller","callee","call",0,2,3),call_site_id("ru",module,"caller","callee","call",1,3,3),call_site_id("ru",module,"caller","callee","call",1,2,4))
  self.assertTrue(all(value!=base for value in variants));self.assertEqual(len(variants),len(set(variants)))
 def test_factory_binds_content(self):
  module=module_id("ru",b"abc");span=SourceSpan("x",1,2,3);call=make_call_site("ru",module,"call","caller","callee",span)
  self.assertEqual(call.id,call_site_id("ru",module,"caller","callee","call",1,2,3))
  with self.assertRaises(ProofSealError):CallSiteEvidence("0"*64,"ru",module,"call","caller","callee",span,(),(),(),(),(),(),(),(),(),())
 def test_assumption_id_content_addressed(self):
  first=make_assumption("sym","i64()",None,"identity",False,"call",True);second=make_assumption("sym","i64()",None,"identity",False,"call",True);changed=make_assumption("sym","i64()",None,"identity",False,"call",False)
  self.assertEqual(first.id,second.id);self.assertNotEqual(first.id,changed.id)
 def test_invalid_identity_inputs(self):
  module=module_id("ru",b"x")
  for kind in ("Call","вызов","other"):
   with self.subTest(kind=kind),self.assertRaises(ProofSealError):call_site_id("ru",module,"a","b",kind,0,1,0)
  for value in (True,-1,MAX_SAFE_INTEGER+1):
   with self.subTest(value=value),self.assertRaises(ProofSealError):call_site_id("ru",module,"a","b","call",value,1,0)
  with self.assertRaises(ProofSealError):call_site_id("ru",module,"a","b","call",2,1,0)
if __name__=="__main__":unittest.main()
