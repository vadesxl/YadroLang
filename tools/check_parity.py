#!/usr/bin/env python3
"""Compare localized Yadro semantic manifests without comparing spellings."""
import json
import sys
from pathlib import Path

REQUIRED={"schema_version","language","surface","localized"}

def configure_utf8(stream):
 reconfigure=getattr(stream,"reconfigure",None)
 if callable(reconfigure):
  try:reconfigure(encoding="utf-8",errors="backslashreplace")
  except (AttributeError,ValueError,OSError):pass
 return stream

def load(path):
 data=json.loads(Path(path).read_text(encoding="utf-8"))
 if not isinstance(data,dict) or set(data)!=REQUIRED:raise ValueError(f"{path}: expected top-level keys {sorted(REQUIRED)}")
 if not isinstance(data["surface"],dict):raise ValueError(f"{path}: surface must be an object")
 if not isinstance(data["localized"],dict):raise ValueError(f"{path}: localized must be an object")
 keywords=data["surface"].get("keywords")
 if not isinstance(keywords,list) or not all(isinstance(item,str) for item in keywords) or len(keywords)!=len(set(keywords)):raise ValueError(f"{path}: keywords must be a unique string list")
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

def cli(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 configure_utf8(sys.stdout);configure_utf8(sys.stderr)
 if len(argv)!=2:
  print("usage: check_parity.py LEFT.json RIGHT.json",file=sys.stderr);return 2
 try:main(argv[0],argv[1]);return 0
 except (OSError,json.JSONDecodeError,ValueError) as error:
  print(f"parity error: {error}",file=sys.stderr);return 1

if __name__=="__main__":raise SystemExit(cli())
