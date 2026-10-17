import os
import sys
from utils import asttools as parser
from utils.codec import instructionset, instructioncategories

basedir = os.path.dirname(os.path.abspath(sys.argv[0]))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

payloadfile = sys.argv[1] if len(sys.argv) > 1 else "./input.lua"
outputfile = sys.argv[2] if len(sys.argv) > 2 else "restored.lua"

payload = ""
with open(payloadfile, "r", encoding="utf-8", errors="replace") as f:
    payload = f.read()

syntaxtree = None
outputbuffer = None

try:
    sys.stdout.write("> parsing payload...")
    syntaxtree = parser.loadast(payload)
    print(" ok")
except Exception as e:
    print(f" fail ({e})")
    sys.exit(1)

try:
    sys.stdout.write("> refining ast...")
    syntaxtree = parser.refineast(syntaxtree, {"renamevariables": True, "format": True})
    print(" ok")
except Exception as e:
    print(e)
    print(" fail")
    sys.exit(1)

modulesdir = os.path.join(basedir, "modules")
for plugin in sorted(os.listdir(modulesdir)):
    pluginpath = os.path.join(modulesdir, plugin)
    if not os.path.isdir(pluginpath) or plugin.startswith("__"):
        continue
    mod = __import__(f"modules.{plugin}.detect", fromlist=["detect", "execute", "enginename"])
    if mod.detect(payload):
        print(f"> engine identified: {mod.enginename}")
        outputbuffer = mod.execute(syntaxtree)
        break

if outputbuffer is not None:
    with open(outputfile, "w", encoding="utf-8") as f:
        f.write(outputbuffer)
    print(f"> saved deobfuscated output to {outputfile}")
else:
    raise RuntimeError("no suitable engine found")
