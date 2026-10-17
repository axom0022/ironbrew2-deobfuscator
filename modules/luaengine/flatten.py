import os
import sys
from utils import asttools as parser
from utils.codec import instructionset, instructioncategories
from utils.eval import computeunary, computebinary

opcodetemplates = {}

filenametoopcode = {
    "move": "Move",
    "loadk": "LoadK",
    "loadbool": "LoadBool",
    "loadnil": "LoadNil",
    "getupval": "GetUpval",
    "getglobal": "GetGlobal",
    "gettable": "GetTable",
    "setglobal": "SetGlobal",
    "setupval": "SetUpval",
    "settable": "SetTable",
    "newtable": "NewTable",
    "self": "Self",
    "add": "Add",
    "sub": "Sub",
    "mul": "Mul",
    "div": "Div",
    "mod": "Mod",
    "pow": "Pow",
    "unm": "Unm",
    "not": "Not",
    "len": "Len",
    "concat": "Concat",
    "jmp": "Jmp",
    "eq": "Eq",
    "lt": "Lt",
    "le": "Le",
    "test": "Test",
    "testset": "TestSet",
    "call": "Call",
    "tailcall": "TailCall",
    "return": "Return",
    "loop": "ForLoop",
    "forloop": "ForLoop",
    "forprep": "ForPrep",
    "tforloop": "TForLoop",
    "setlist": "SetList",
    "close": "Close",
    "closure": "Closure",
    "vararg": "VarArg",
    "custom": "Move",
}


def buildliteral(n):
    if isinstance(n, float) and int(n) == n:
        n = int(n)
    s = str(n)
    return {
        "Type": "NumberLiteral",
        "Source": s,
        "Token": {"Type": "Number", "LeadingWhite": "", "Source": s},
        "GetFirstToken": lambda: None,
        "GetLastToken": lambda: None,
    }


aliasknown = None
aliasunknown = None
compiledtemplates = []
knowntokenset = frozenset()


def traceflow(enum, tokens, clause=None, parent=None):
    clause = clause or tokens["Clauses"]
    if clause is None:
        return parent
    cond = clause["Condition"]
    elseclauses = clause.get("ElseClauseList", [])
    if cond["Type"] != "BinopExpr" or cond["Lhs"]["Type"] != "VariableExpr":
        return parent
    if cond["Lhs"]["Variable"]["Name"] != tokens["Enum"]:
        return parent
    if cond["Rhs"]["Type"] == "UnopExpr":
        val = computeunary(cond["Rhs"])
        if val is not None:
            cond["Rhs"] = buildliteral(val)
        else:
            return None
    elif cond["Rhs"]["Type"] != "NumberLiteral":
        raise RuntimeError("unhandled comparison")

    def extractbody(c):
        stmts = c["Body"]["StatementList"]
        if stmts and stmts[0]["Type"] == "IfStat":
            return traceflow(enum, tokens, stmts[0], stmts)
        return stmts

    if computebinary(enum, cond["Token_Op"]["Source"], cond["Rhs"]["Token"]["Source"]):
        return extractbody(clause)

    for i in range(len(elseclauses)):
        clause = elseclauses[i]
        cond = clause.get("Condition")
        if clause["ClauseType"] == "elseif":
            if cond["Rhs"]["Type"] == "UnopExpr":
                val = computeunary(cond["Rhs"])
                if val is not None:
                    cond["Rhs"] = buildliteral(val)
                else:
                    return None
            elif cond["Rhs"]["Type"] != "NumberLiteral":
                raise RuntimeError("unhandled comparison")
            if computebinary(enum, cond["Token_Op"]["Source"], cond["Rhs"]["Token"]["Source"]):
                return extractbody(clause)
        elif clause["ClauseType"] == "else":
            return extractbody(clause)
    return None


def matchast(instructions, samplestmts, thorough):
    def match(a, b):
        if a["Type"] != b["Type"]:
            if b["Type"] == "NumberLiteral" and a["Type"] == "UnopExpr":
                val = computeunary(a)
                if val is not None:
                    a = buildliteral(val)
                else:
                    return False
            else:
                return False
        t = a["Type"]
        if t == "AssignmentStat":
            return listmatch(a["Rhs"], b["Rhs"]) and listmatch(a["Lhs"], b["Lhs"])
        elif t == "IndexExpr":
            names = True
            if thorough and "Variable" in a["Base"] and a["Base"]["Variable"] is not None and b["Base"]["Type"] == "VariableExpr":
                names = a["Base"]["Variable"]["Name"] == b["Base"]["Token"]["Source"]
            return names and match(a["Base"], b["Base"]) and match(a["Index"], b["Index"])
        elif t == "VariableExpr":
            if thorough and "Variable" in a and "Token" in b:
                bsrc = b["Token"]["Source"]
                if bsrc in knowntokenset:
                    return a["Variable"]["Name"] == bsrc
            return True
        elif t == "NumberLiteral":
            return a["Token"]["Source"] == b["Token"]["Source"]
        elif t == "LocalVarStat":
            return listmatch(a["ExprList"], b["ExprList"])
        elif t == "CallExprStat":
            e1 = a["Expression"]
            e2 = b["Expression"]
            return match(e1["Base"], e2["Base"]) and listmatch(e1["FunctionArguments"]["ArgList"], e2["FunctionArguments"]["ArgList"])
        elif t == "CallExpr":
            return match(a["Base"], b["Base"]) and listmatch(a["FunctionArguments"]["ArgList"], b["FunctionArguments"]["ArgList"])
        elif t == "BinopExpr":
            t1 = a["Token_Op"]
            t2 = b["Token_Op"]
            return t1["Source"] == t2["Source"] and match(a["Rhs"], b["Rhs"]) and match(a["Lhs"], b["Lhs"])
        elif t == "DoStat":
            return listmatch(a["Body"]["StatementList"], b["Body"]["StatementList"])
        elif t == "ReturnStat":
            return listmatch(a["ExprList"], b["ExprList"])
        elif t in ("NilLiteral", "BreakStat"):
            return True
        elif t == "TableLiteral":
            e1 = a.get("EntryList", a.get("Fields", []))
            e2 = b.get("EntryList", b.get("Fields", []))
            if len(e1) != len(e2):
                return False
            return all(match(x["Value"], y["Value"]) for x, y in zip(e1, e2))
        elif t == "NumericForStat":
            return listmatch(a["RangeList"], b["RangeList"]) and listmatch(a["Body"]["StatementList"], b["Body"]["StatementList"])
        elif t == "ParenExpr":
            return match(a["Expression"], b["Expression"])
        elif t == "UnopExpr":
            return a["Token_Op"]["Source"] == b["Token_Op"]["Source"] and match(a["Rhs"], b["Rhs"])
        elif t == "IfStat":
            if not match(a["Condition"], b["Condition"]):
                return False
            if thorough and not listmatch(a["Body"]["StatementList"], b["Body"]["StatementList"]):
                return False
            o1 = a["ElseClauseList"]
            o2 = b["ElseClauseList"]
            if len(o1) != len(o2):
                return False
            for i in range(len(o1)):
                if o1[i]["ClauseType"] != o2[i]["ClauseType"]:
                    return False
                if not listmatch(o1[i]["Body"]["StatementList"], b["ElseClauseList"][i]["Body"]["StatementList"]):
                    return False
            return listmatch(a["Body"]["StatementList"], b["Body"]["StatementList"])
        return False

    def listmatch(a, b):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if not match(a[i], b[i]):
                return False
        return True

    return listmatch(instructions, samplestmts)


def findmatchingtemplate(instructions, nolocal=False):
    for tmpl in compiledtemplates:
        v = tmpl["variant"]
        if "Match" in v and callable(v["Match"]):
            if v["Match"](instructions):
                return tmpl
        elif "String" in v:
            samplestmts = tmpl["astnolocal"] if nolocal else tmpl["astnormal"]
            if matchast(instructions, samplestmts, v.get("Thorough", False)):
                return tmpl
    return None


def applytemplate(tmpl, operand, pc):
    inst = dict(operand)
    inst["PC"] = pc
    inst.setdefault("A", 0)
    inst.setdefault("B", 0)
    inst.setdefault("C", 0)
    res = tmpl["variant"]["Create"](inst)
    if isinstance(res, dict):
        inst = res
    opname = tmpl["opname"]
    inst["OpCode"] = instructionset.index(opname)
    inst["OpName"] = instructionset[inst["OpCode"]]
    inst["Type"] = instructioncategories[inst["OpCode"]]
    return inst


def issuperjump(s, tokens):
    if s["Type"] != "AssignmentStat" or not s.get("Rhs") or not s.get("Lhs"):
        return False
    r = s["Rhs"][0]
    l = s["Lhs"][0]
    return (
        r["Type"] == "BinopExpr"
        and r["Lhs"]["Type"] == "VariableExpr"
        and r["Lhs"]["Variable"]["Name"] == tokens["InstrPoint"]
        and r["Rhs"]["Type"] == "NumberLiteral"
        and r["Rhs"]["Token"]["Source"] == "1"
        and l["Type"] == "VariableExpr"
        and l["Variable"]["Name"] == tokens["InstrPoint"]
    )


def resolveinstruction(instructions, operands, pc, tokens, nolocal=False):
    tmpl = findmatchingtemplate(instructions, nolocal)
    if tmpl is not None:
        return applytemplate(tmpl, operands[pc], pc)

    if any(issuperjump(s, tokens) for s in instructions):
        container = {
            "Instructions": [],
            "SuperInstruction": True,
            "MatchedInstructions": [],
            "SubCount": sum(1 for s in instructions if issuperjump(s, tokens)),
        }
        sub = []
        container["Instructions"].append(sub)
        idx = 0
        while idx < len(instructions):
            stmt = instructions[idx]
            if issuperjump(stmt, tokens):
                idx += 2
                sub = []
                container["Instructions"].append(sub)
                continue
            elif stmt["Type"] == "LocalVarStat":
                idx += 1
                continue
            else:
                sub.append(stmt)
                idx += 1
        for i in range(len(container["Instructions"])):
            sublist = container["Instructions"][i]
            matched = resolveinstruction(sublist, operands, pc + i, tokens, True)
            if matched is not None:
                matched["Enum"] = i
                container["MatchedInstructions"].append(matched)
            else:
                container["MatchedInstructions"].append({
                    "PlaceHolder": True,
                    "Enum": i,
                })
        return container
    return None


def flatten(vmstate):
    global opcodetemplates, aliasknown, aliasunknown, compiledtemplates, knowntokenset
    version = vmstate["Version"]
    basedir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if not os.path.isdir(os.path.join(basedir, "modules")):
        basedir = os.getcwd()
    if version == "IronBrew V2.7.0":
        verfolder = "2.7.0"
    elif version in ("IronBrew V2.7.1", "AztupBrew V2.7.2"):
        verfolder = "2.7.1"
    else:
        raise RuntimeError(f"unsupported version: {version}")

    path = os.path.join(basedir, "modules", "luaengine", "opcodes", verfolder)
    opcodetemplates = {}

    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        stem = fname[:-3]
        opname = filenametoopcode.get(stem.lower(), stem)
        fpath = os.path.join(path, fname)
        modenv = {}
        with open(fpath, "r", encoding="utf-8") as f:
            exec(f.read(), modenv)
        variants = {}
        for k, v in modenv.items():
            if not k.startswith("_") and isinstance(v, dict) and ("String" in v or "Match" in v):
                variants[k] = v
        if opname in opcodetemplates:
            opcodetemplates[opname].update(variants)
        else:
            opcodetemplates[opname] = variants

    tokens = vmstate["Tokens"]
    knowntokenset = frozenset(
        v for k, v in tokens.items() if isinstance(v, str) and v
    )

    def knownsub(s):
        res = s.replace("OP_A", "2").replace("OP_B", "3")
        res = res.replace("InstrPoint", tokens.get("InstrPoint") or "InstrPoint")
        res = res.replace("Upvalues", tokens.get("Upvalues") or "Upvalues")
        res = res.replace("Unpack", tokens.get("Unpack") or "Unpack")
        res = res.replace("Const", tokens.get("Const") or "Const")
        res = res.replace("Wrap", tokens.get("Wrap") or "Wrap")
        res = res.replace("Inst", tokens.get("Inst") or "Inst")
        res = res.replace("Top", tokens.get("Top") or "Top")
        res = res.replace("Stk", tokens.get("Stk") or "Stk")
        res = res.replace("Env", tokens.get("Env") or "Env")
        if version == "IronBrew V2.7.0":
            res = res.replace("OP_C", "5")
        else:
            res = res.replace("OP_C", "4")
        return res

    def unknownsub(s):
        res = s.replace("[2", "[OP_A").replace("[3", "[OP_B")
        if version == "IronBrew V2.7.0":
            res = res.replace("[5", "[OP_C")
        else:
            res = res.replace("[4", "[OP_C")
        for key in ("InstrPoint", "Upvalues", "Unpack", "Const", "Wrap", "Inst", "Top", "Stk", "Env"):
            tokval = tokens.get(key)
            if tokval:
                res = res.replace(tokval, key)
        return res

    aliasknown = knownsub
    aliasunknown = unknownsub

    compiledtemplates = []
    for opname, variants in opcodetemplates.items():
        for vname, v in variants.items():
            astnormal = None
            astnolocal = None
            if "String" in v:
                snorm = knownsub(v["String"])
                snoloc = knownsub(v["String"].replace("local", ""))
                astnormal = parser.loadast(snorm)["StatementList"]
                astnolocal = parser.loadast(snoloc)["StatementList"]
            compiledtemplates.append({
                "opname": opname,
                "vname": vname,
                "variant": v,
                "astnormal": astnormal,
                "astnolocal": astnolocal,
            })

    enumcache = {}

    def resolveenumdescriptor(enum):
        if enum in enumcache:
            return enumcache[enum]
        found = traceflow(enum, tokens)
        if found is None:
            enumcache[enum] = None
            return None
        tmpl = findmatchingtemplate(found, False)
        if tmpl is not None:
            desc = {"issuper": False, "tmpl": tmpl}
            enumcache[enum] = desc
            return desc
        if any(issuperjump(s, tokens) for s in found):
            subs = []
            sub = []
            subs.append(sub)
            subcount = 0
            idx = 0
            while idx < len(found):
                stmt = found[idx]
                if issuperjump(stmt, tokens):
                    subcount += 1
                    idx += 2
                    sub = []
                    subs.append(sub)
                    continue
                elif stmt["Type"] == "LocalVarStat":
                    idx += 1
                    continue
                else:
                    sub.append(stmt)
                    idx += 1
            subtmpls = []
            for i, sublist in enumerate(subs):
                st = findmatchingtemplate(sublist, True)
                if st is None:
                    raw = parser.displayast({"Type": "StatList", "StatementList": sublist, "SemicolonList": []})
                    raise RuntimeError(f"unmatched sub-instruction #{i+1} in #{enum}:\n{aliasunknown(raw)}")
                subtmpls.append(st)
            desc = {"issuper": True, "subcount": subcount, "subtmpls": subtmpls}
            enumcache[enum] = desc
            return desc
        raw = parser.displayast({"Type": "StatList", "StatementList": found, "SemicolonList": []})
        raise RuntimeError(f"unmatched instruction #{enum}:\n{aliasunknown(raw)}")

    def parseblock(chunk):
        insts = chunk["Instructions"]
        protos = chunk["Prototypes"]
        matchedinsts = []
        pc = 0
        while pc < len(insts):
            if insts[pc].get("IsData"):
                pc += 1
                continue
            enum = insts[pc]["Enum"]
            desc = resolveenumdescriptor(enum)
            if desc is not None:
                if desc["issuper"]:
                    for i, st in enumerate(desc["subtmpls"]):
                        if pc + i < len(insts):
                            subinst = applytemplate(st, insts[pc + i], len(matchedinsts))
                            subinst["Enum"] = i
                            matchedinsts.append(subinst)
                    pc += desc["subcount"] + 1
                else:
                    matched = applytemplate(desc["tmpl"], insts[pc], len(matchedinsts))
                    matchedinsts.append(matched)
                    pc += 1
            else:
                pc += 1

        for i in range(len(protos)):
            protos[i] = parseblock(protos[i])
        chunk["Instructions"] = matchedinsts
        return chunk

    devirtualized = parseblock(vmstate["Chunk"])

    def markvararg(chunk):
        for i in range(len(chunk["Instructions"])):
            inst = chunk["Instructions"][i]
            if instructionset[inst["OpCode"]] == "VarArg":
                chunk["VarArg"] = True
            elif instructionset[inst["OpCode"]] == "Closure":
                protoidx = inst["B"]
                if 0 <= protoidx < len(chunk["Prototypes"]):
                    chunk["Prototypes"][protoidx]["Upvalues"] = inst.get("UpvalueCount", inst.get("C") or 0)
        for i in range(len(chunk["Prototypes"])):
            markvararg(chunk["Prototypes"][i])

    markvararg(devirtualized)
    print(" ok")
    return devirtualized


def dummyhelper():
    pass
