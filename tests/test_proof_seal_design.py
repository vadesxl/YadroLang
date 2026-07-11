import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAX_SAFE_INTEGER=9_007_199_254_740_991
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
  subject=self.schema()["properties"]["subject"];self.assertEqual("yadro-policy-1.0",subject["properties"]["policy_schema_version"]["const"]);self.assertEqual("yadro-llvm-normalization-1.0",subject["properties"]["llvm_normalization_version"]["const"])
 def test_nested_objects_reject_unknown_fields(self):
  schema=self.schema();objects=[schema["properties"]["trust"],schema["properties"]["compiler"],schema["properties"]["subject"],schema["properties"]["analysis"],schema["$defs"]["span"],schema["$defs"]["callSite"],schema["$defs"]["assumption"],schema["$defs"]["fixpoint"]];self.assertTrue(all(item.get("additionalProperties") is False for item in objects))
 def test_hashes_collection_bounds_and_safe_integers(self):
  schema=self.schema();self.assertEqual("^[0-9a-f]{64}$",schema["$defs"]["sha256"]["pattern"]);self.assertEqual(10000,schema["properties"]["analysis"]["properties"]["call_sites"]["maxItems"]);self.assertEqual(2000,schema["properties"]["analysis"]["properties"]["assumptions"]["maxItems"])
  self.assertEqual(MAX_SAFE_INTEGER,schema["$defs"]["safeInteger"]["maximum"]);self.assertEqual(0,schema["$defs"]["safeInteger"]["minimum"]);self.assertEqual(MAX_SAFE_INTEGER,schema["$defs"]["positiveSafeInteger"]["maximum"]);self.assertEqual(1,schema["$defs"]["positiveSafeInteger"]["minimum"])
  for field in ("start_byte","end_byte","ordinal"):self.assertEqual("#/$defs/safeInteger",schema["$defs"]["span"]["properties"][field]["$ref"])
  self.assertEqual("#/$defs/safeInteger",schema["$defs"]["fixpoint"]["properties"]["updates"]["$ref"]);self.assertEqual("#/$defs/positiveSafeInteger",schema["$defs"]["fixpoint"]["properties"]["bound"]["$ref"])
 def test_patterns_are_syntactically_valid(self):
  def walk(value):
   if isinstance(value,dict):
    if "pattern" in value:re.compile(value["pattern"])
    for child in value.values():walk(child)
   elif isinstance(value,list):
    for child in value:walk(child)
  walk(self.schema())
if __name__=="__main__":unittest.main()
