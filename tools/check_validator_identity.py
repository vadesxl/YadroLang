#!/usr/bin/env python3
"""Fail unless two validator files are byte-identical."""
import hashlib
import sys
from pathlib import Path

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main(left,right):
 left_digest,right_digest=digest(left),digest(right)
 if left_digest!=right_digest:raise ValueError(f"parity validator drift: {left_digest} != {right_digest}")
 print(f"validator sha256 {left_digest}")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: check_validator_identity.py LEFT RIGHT")
 try:main(sys.argv[1],sys.argv[2])
 except (OSError,ValueError) as error:print(error,file=sys.stderr);raise SystemExit(1)
