import json
from src.proof_seal import canonical_bytes,seal
from tests.proof_seal_fixtures import minimal_core,rich_core
def valid_bytes(rich=True):return canonical_bytes(seal(rich_core() if rich else minimal_core()))
def parsed(rich=True):return json.loads(valid_bytes(rich))
def encoded(value,sort=True,indent=None,ascii=False):return (json.dumps(value,ensure_ascii=ascii,sort_keys=sort,separators=None if indent else (",",":"),indent=indent)+"\n").encode("utf-8")
