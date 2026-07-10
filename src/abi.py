import hashlib,re
ABI_VERSION=1
def symbol(kind,name):
 safe=re.sub(r"[^A-Za-z0-9_]","_",name)[:32].strip("_") or "symbol";digest=hashlib.sha256(name.encode("utf-8")).hexdigest()[:16];kind_safe=re.sub(r"[^A-Za-z0-9_]","_",kind);return f"yadro_{kind_safe}_{safe}_{digest}"
def external_symbol(name):return symbol("abi_v1",name)
