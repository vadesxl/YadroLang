#!/usr/bin/env python3
"""Compare two localized Yadro semantic manifests without comparing spellings."""
import json
import sys
from pathlib import Path

def load(path):
 data=json.loads(Path(path).read_text(encoding="utf-8"))
 required={"schema_version","language","surface","localized"}
 if set(data)!=required:raise ValueError(f"{path}: expected top-level keys {sorted(required)}")
 keywords=data["surface"].get("keywords")
 if not isinstance(keywords,list) or len(keywords)!=len(set(keywords)):raise ValueError(f"{path}: keywords must be a unique list")
 if set(data["localized"])!=set(keywords):raise ValueError(f"{path}: localized keys must exactly match semantic keywords")
 if not all(isinstance(value,str) and value for value in data["localized"].values()):raise ValueError(f"{path}: localized spellings must be non-empty strings")
 return data

def main(left_path,right_path):
 left,right=load(left_path),load(right_path)
 if left["language"]==right["language"]:raise ValueError("manifests must describe different localizations")
 if left["schema_version"]!=right["schema_version"]:raise ValueError("schema versions differ")
 if left["surface"]!=right["surface"]:
  left_text=json.dumps(left["surface"],ensure_ascii=False,sort_keys=True,indent=2)
  right_text=json.dumps(right["surface"],ensure_ascii=False,sort_keys=True,indent=2)
  raise ValueError(f"semantic surfaces differ\nLEFT:\n{left_text}\nRIGHT:\n{right_text}")
 print(f"semantic parity OK: {left['language']} <-> {right['language']}")

if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: check_parity.py LEFT.json RIGHT.json")
 try:main(sys.argv[1],sys.argv[2])
 except (OSError,json.JSONDecodeError,ValueError) as error:print(f"parity error: {error}",file=sys.stderr);raise SystemExit(1)
