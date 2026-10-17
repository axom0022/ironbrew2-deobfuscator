import re
import sys
from .transform import extractcontext, parsebytecode, emitcode
from .flatten import flatten
from utils import asttools as parser

_PATTERNS = [
    re.compile(r"return\s+table\.concat\s*\([_\-a-zA-Z0-9]+\)"),
    re.compile(r"return\s+[_\-a-zA-Z0-9]+\s*\([^()]*,\s*\{\s*\}\s*,"),
    re.compile(r"bit\s+and\s+bit\.bxor\s+or\s+function\s*\("),
    re.compile(r"getfenv\s+or\s+function\s*\(\s*\)\s*return\s+_ENV\s+end"),
    re.compile(r"local\s+[_\-a-zA-Z0-9]+\s*=\s*table\.concat"),
]


def detect(source):
    head = source[:16384]
    tail = source[-8192:] if len(source) > 16384 else ""
    sample = head + "\n" + tail
    return any(p.search(sample) for p in _PATTERNS)


def execute(astroot):
    sys.stdout.write("> extracting vm state...")
    parser.resolvearithmetic(astroot)
    vmstate = extractcontext(astroot["StatementList"], True)
    sys.stdout.write("> decoding bytecode...")
    vmstate = parsebytecode(vmstate, True)
    sys.stdout.write("> flattening vm...")
    vmstate = flatten(vmstate)
    return emitcode(vmstate)


enginename = "IronBrew2"
