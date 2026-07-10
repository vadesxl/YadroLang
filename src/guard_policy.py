# -*- coding: utf-8 -*-
import json
from pathlib import Path
from src import guard
ALLOWED_KEYS=frozenset({"version","sources","sinks","sanitizers"})
def strict_load_policy(path):
 data=json.loads(Path(path).read_text(encoding="utf-8"))
 if not isinstance(data,dict):raise guard.ОшибкаПолитики("корень policy должен быть объектом")
 unknown=sorted(set(data)-ALLOWED_KEYS)
 if unknown:raise guard.ОшибкаПолитики(f"неизвестные поля policy: {', '.join(unknown)}")
 if data.get("version")!="1.0":raise guard.ОшибкаПолитики("policy.version должна быть '1.0'")
 for key in ("sources","sinks","sanitizers"):
  if key in data and not isinstance(data[key],dict):raise guard.ОшибкаПолитики(f"policy.{key} должна быть объектом")
 for name,label in data.get("sources",{}).items():
  if not isinstance(name,str) or label not in guard.ИЗВЕСТНЫЕ_МЕТКИ:raise guard.ОшибкаПолитики(f"неверный source: {name!r}")
 for name,capability in data.get("sinks",{}).items():
  if not isinstance(name,str) or not isinstance(capability,str) or not capability:raise guard.ОшибкаПолитики(f"неверный sink: {name!r}")
 for name,labels in data.get("sanitizers",{}).items():
  if not isinstance(name,str) or not isinstance(labels,list) or not set(labels)<=guard.ИЗВЕСТНЫЕ_МЕТКИ:raise guard.ОшибкаПолитики(f"неверный sanitizer: {name!r}")
 builtins=set(guard._BASE_ИСТОЧНИКИ)|set(guard._BASE_СТОКИ)|set(guard._BASE_САНИТАЙЗЕРЫ);custom=set(data.get("sources",{}))|set(data.get("sinks",{}))|set(data.get("sanitizers",{}));collisions=sorted(builtins&custom)
 if collisions:raise guard.ОшибкаПолитики(f"custom policy конфликтует с builtin: {', '.join(collisions)}")
 return data
