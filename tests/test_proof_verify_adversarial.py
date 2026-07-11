import random,unittest
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import valid_bytes
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
if __name__=="__main__":unittest.main()
