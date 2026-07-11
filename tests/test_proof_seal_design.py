import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ТестыProofSealDesign(unittest.TestCase):
 def schema(self):return json.loads((ROOT/"proof-seal.schema.json").read_text(encoding="utf-8"),object_pairs_hook=self.no_duplicates)
 @staticmethod
 def no_duplicates(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError(f"duplicate JSON key: {key}")
   result[key]=value
  return result
 def test_schema_is_strict_unsigned_v1(self):
  schema=self.schema();self.assertEqual("yadro-proof-seal-1.0",schema["properties"]["schema"]["const"]);self.assertFalse(schema["additionalProperties"])
  trust=schema["properties"]["trust"];self.assertEqual("unsigned",trust["properties"]["mode"]["const"]);self.assertEqual("not-provided",trust["properties"]["authenticity"]["const"])
 def test_versions_are_visible_before_hashing(self):
  subject=self.schema()["properties"]["subject"];self.assertIn("policy_schema_version",subject["required"]);self.assertIn("llvm_normalization_version",subject["required"])
 def test_call_site_identity_is_recomputable(self):
  call=self.schema()["$defs"]["callSite"];self.assertFalse(call["additionalProperties"])
  self.assertIn("module_id",call["required"]);self.assertIn("semantic_kind",call["required"]);self.assertEqual("call",call["properties"]["semantic_kind"]["const"])
  text=(ROOT/"CALL_SITE_IDENTITY.md").read_text(encoding="utf-8");self.assertIn("YADRO-CALL-SITE\\0",text);self.assertIn("Identity is not completeness",text)
 def test_nested_objects_reject_unknown_fields(self):
  schema=self.schema();objects=[schema["properties"]["trust"],schema["properties"]["compiler"],schema["properties"]["subject"],schema["properties"]["analysis"],schema["$defs"]["span"],schema["$defs"]["callSite"],schema["$defs"]["assumption"],schema["$defs"]["fixpoint"]];self.assertTrue(all(item.get("additionalProperties") is False for item in objects))
 def test_hashes_and_bounds_are_explicit(self):
  schema=self.schema();self.assertEqual("^[0-9a-f]{64}$",schema["$defs"]["sha256"]["pattern"]);self.assertEqual(9007199254740991,schema["$defs"]["safeInteger"]["maximum"])
 def test_patterns_are_syntactically_valid(self):
  def walk(value):
   if isinstance(value,dict):
    if "pattern" in value:re.compile(value["pattern"])
    for child in value.values():walk(child)
   elif isinstance(value,list):
    for child in value:walk(child)
  walk(self.schema())
if __name__=="__main__":unittest.main()
