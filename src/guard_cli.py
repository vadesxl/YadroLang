import sys
from src import guard,mcp_guard_v2
def _utf8(stream):
 reconfigure=getattr(stream,"reconfigure",None)
 if callable(reconfigure):
  try:reconfigure(encoding="utf-8",errors="backslashreplace")
  except (AttributeError,ValueError,OSError):pass
 return stream
def run(argv=None,stdout=sys.stdout,stderr=sys.stderr):
 args=list(sys.argv[1:] if argv is None else argv)
 _utf8(stdout);_utf8(stderr)
 if args and args[0]=="mcp":return mcp_guard_v2.run(args[1:],stdout,stderr)
 return guard.run(args,stdout,stderr)
def main():raise SystemExit(run())
if __name__=="__main__":main()
