import unittest
from src.proof_seal import MAX_SEAL_BYTES,MAX_SAFE_INTEGER
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import valid_bytes
class ProofVerifyReaderTests(unittest.TestCase):
 def test_valid(self):self.assertTrue(verify_bytes(valid_bytes()).valid)
 def test_input_bounds(self):
  for data,code in ((b"",ProofReadError.code),("x",ProofReadError.code),(b"x"*(MAX_SEAL_BYTES+1),ProofReadError.code),(b"\xef\xbb\xbf{}",ProofEncodingError.code),(b"\xff",ProofEncodingError.code)):
   with self.subTest(code=code):self.assertEqual(code,inspect_bytes(data).diagnostic_code)
 def test_depth_and_strings(self):
  self.assertNotEqual(ProofDepthError.code,inspect_bytes(b'{"schema":"'+b'['*30+b'"}').diagnostic_code)
  deep=("["*17+"0"+"]"*17).encode();self.assertEqual(ProofDepthError.code,inspect_bytes(deep).diagnostic_code)
  self.assertEqual(ProofDepthError.code,inspect_bytes(b'{"x":"unterminated}').diagnostic_code)
 def test_syntax(self):
  for data in (b"{",b"{} trailing",b'{"x":"\x01"}'):
   self.assertIn(inspect_bytes(data).diagnostic_code,{ProofSyntaxError.code,ProofDepthError.code,ProofVersionError.code})
 def test_nonstandard_and_safe_integer_bounds_are_controlled(self):
  accepted=(0,1,MAX_SAFE_INTEGER-1,MAX_SAFE_INTEGER)
  for value in accepted:
   data=(f'{{"schema":{value}}}').encode();self.assertEqual(ProofVersionError.code,inspect_bytes(data).diagnostic_code)
  rejected=(MAX_SAFE_INTEGER+1,9_999_999_999_999_999,18_446_744_073_709_551_615,-1)
  for value in rejected:
   with self.subTest(value=value):self.assertEqual(ProofValueError.code,inspect_bytes((f'{{"schema":{value}}}').encode()).diagnostic_code)
  for data in (b'{"schema":NaN}',b'{"schema":1.5}'):
   self.assertEqual(ProofValueError.code,inspect_bytes(data).diagnostic_code)
if __name__=="__main__":unittest.main()
