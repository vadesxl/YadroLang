import dataclasses,unittest
from src.proof_seal import *
from tests.proof_seal_fixtures import minimal_core,rich_core,ZERO
class ProofSealModelTests(unittest.TestCase):
 def test_minimal_and_rich_models(self):
  self.assertEqual((),minimal_core().analysis.call_sites);self.assertEqual("unsigned",minimal_core().trust.mode)
  core=rich_core();self.assertEqual(("Здоровье","ПДн"),core.analysis.call_sites[0].incoming_labels);self.assertEqual(1,len(core.analysis.assumptions))
 def test_factories_canonicalize_permutations(self):
  self.assertEqual(canonical_bytes(rich_core(False)),canonical_bytes(rich_core(True)))
 def test_frozen(self):
  with self.assertRaises(dataclasses.FrozenInstanceError):minimal_core().trust.mode="signed"
 def test_visible_versions(self):
  subject=minimal_core().subject;self.assertEqual(POLICY_VERSION,subject.policy_schema_version);self.assertEqual(LLVM_NORMALIZATION_VERSION,subject.llvm_normalization_version)
 def test_span_and_path(self):
  self.assertEqual("src/x.яд",SourceSpan("src/x.яд",0,3,1).module_path)
  for path in ("/x","C:/x","../x","a//b","a\\b","./x"):
   with self.subTest(path=path),self.assertRaises(ProofSealError):SourceSpan(path,0,0,0)
 def test_hash_validation(self):
  for value in ("A"*64,"0"*63,"g"*64):
   with self.subTest(value=value),self.assertRaises(ProofSealError):SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,value,ZERO,ZERO,ZERO,"x","elf-object")
if __name__=="__main__":unittest.main()
