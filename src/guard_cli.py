import sys
from src import guard,mcp_guard_v2
def run(argv=None,stdout=sys.stdout,stderr=sys.stderr):
 args=list(sys.argv[1:] if argv is None else argv)
 if args and args[0]=="mcp":return mcp_guard_v2.run(args[1:],stdout,stderr)
 return guard.run(args,stdout,stderr)
def main():raise SystemExit(run())
if __name__=="__main__":main()
