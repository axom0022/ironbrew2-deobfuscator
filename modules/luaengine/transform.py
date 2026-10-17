import re
import struct
from utils.eval import decompress, decode, gbit, bxor
from utils.codec import decompilechunk, serializeluac


def unwrapexpr(node):
    while isinstance(node, dict) and node.get("Type") == "ParenExpr":
        node = node["Expression"]
    return node


def extractbytestring(strnode):
    src = strnode["Token"]["Source"]
    m = re.search(r"[A-Za-z0-9\\]+=*", src)
    return m.group(0) if m else src


def extractcontext(statements, flag=True):
    isaztup = len(statements) > 0 and statements[0].get("Type") == "ReturnStat"

    if isaztup:
        expr = statements[0]["ExprList"][0]
        base = expr.get("Base", expr)
        base = unwrapexpr(base)
        statements = base["Body"]["StatementList"]

    functions = [s for s in statements if s.get("Type") == "LocalFunctionStat"]
    variables = [s for s in statements if s.get("Type") == "LocalVarStat"]

    gbits16 = None
    for s in functions:
        bodystmts = s["FunctionStat"]["Body"]["StatementList"]
        for x in bodystmts:
            if x.get("Type") == "AssignmentStat" and x.get("Rhs"):
                rhs0 = x["Rhs"][0]
                if rhs0.get("Type") == "BinopExpr" and rhs0["Rhs"].get("Type") == "NumberLiteral" and rhs0["Rhs"]["Token"]["Source"] == "2":
                    gbits16 = s
                    break
        if gbits16 is not None:
            break

    version = f"{'AztupBrew' if isaztup else 'IronBrew'} V2.7.{2 if isaztup else (1 if gbits16 else 0)}"

    gbits32 = None
    for s in functions:
        bodystmts = s["FunctionStat"]["Body"]["StatementList"]
        if len(bodystmts) > 1 and bodystmts[1].get("Type") == "AssignmentStat":
            rhs0 = bodystmts[1]["Rhs"][0]
            if rhs0.get("Type") == "CallExpr" and len(rhs0["FunctionArguments"].get("ArgList", [])) >= 2:
                gbits32 = s
                break

    xorkey = int(gbits32["FunctionStat"]["Body"]["StatementList"][1]["Rhs"][0]["FunctionArguments"]["ArgList"][1]["Token"]["Source"])

    compression = len(functions[0]["FunctionStat"]["Body"]["StatementList"]) >= 3

    bytestring = ""
    if compression:
        for s in variables:
            if s.get("ExprList") and s["ExprList"][0].get("Type") == "CallExpr":
                args = s["ExprList"][0]["FunctionArguments"].get("ArgList", [])
                if args and args[0].get("Type") == "StringLiteral":
                    bytestring = extractbytestring(args[0])
                    break
    if not bytestring:
        for s in variables:
            if s.get("ExprList") and s["ExprList"][0].get("Type") == "StringLiteral":
                bytestring = extractbytestring(s["ExprList"][0])
                compression = False
                break

    bytecode = decompress(bytestring, xorkey) if compression else decode(bytestring, xorkey)

    deserializefn = None
    for s in functions:
        bodystmts = s["FunctionStat"]["Body"]["StatementList"]
        forcount = sum(1 for st in bodystmts if st.get("Type") == "NumericForStat")
        if forcount > 1:
            deserializefn = s
            break

    dbody = deserializefn["FunctionStat"]["Body"]["StatementList"]
    dname = deserializefn["FunctionStat"]["NameChain"][0]["Source"]

    bformat = []
    cformat = {}
    primary = xorkey
    secondary = 0
    tertiary = 0

    for operation in dbody:
        typ = operation.get("Type")
        if typ == "NumericForStat" and operation["RangeList"][1].get("Type") == "VariableExpr":
            bformat.append("Constants")
            ifstats = [st for st in operation["Body"]["StatementList"] if st.get("Type") == "IfStat"]
            if len(ifstats) > 1:
                cformat["Bool"] = int(unwrapexpr(ifstats[0]["Condition"])["Rhs"]["Token"]["Source"])
                cformat["Float"] = int(unwrapexpr(ifstats[1]["Condition"])["Rhs"]["Token"]["Source"])
                cformat["String"] = int(unwrapexpr(ifstats[2]["Condition"])["Rhs"]["Token"]["Source"])
            else:
                checks = ifstats[0]
                clauses = checks.get("ElseClauseList", [])
                cformat["Bool"] = int(unwrapexpr(checks["Condition"])["Rhs"]["Token"]["Source"])
                cformat["Float"] = int(unwrapexpr(clauses[0]["Condition"])["Rhs"]["Token"]["Source"])
                cformat["String"] = int(unwrapexpr(clauses[1]["Condition"])["Rhs"]["Token"]["Source"])
        elif typ == "NumericForStat" and operation["Body"]["StatementList"] and operation["Body"]["StatementList"][0].get("Type") == "LocalVarStat":
            bformat.append("Instructions")
            if version == "IronBrew V2.7.0":
                callvars = [
                    st for st in operation["Body"]["StatementList"]
                    if st.get("Type") == "LocalVarStat" and st.get("ExprList") and st["ExprList"][0].get("Type") == "CallExpr"
                ]
                if len(callvars) >= 2:
                    secondary = int(callvars[0]["ExprList"][0]["FunctionArguments"]["ArgList"][1]["Token"]["Source"])
                    tertiary = int(callvars[1]["ExprList"][0]["FunctionArguments"]["ArgList"][1]["Token"]["Source"])
        elif (
            typ == "NumericForStat"
            and operation["Body"]["StatementList"]
            and operation["Body"]["StatementList"][0].get("Type") == "AssignmentStat"
            and operation["Body"]["StatementList"][0]["Rhs"][0].get("Type") == "CallExpr"
            and operation["Body"]["StatementList"][0]["Rhs"][0]["Base"]["Token"]["Source"] == dname
        ):
            bformat.append("Prototypes")
        elif typ == "NumericForStat":
            bformat.append("Debug")
        elif typ == "AssignmentStat":
            rhstype = operation["Rhs"][0].get("Type")
            if rhstype == "CallExpr":
                bformat.append("Parameters")
            elif rhstype == "VariableExpr":
                continue

    wrap = None
    for s in functions:
        bodystmts = s["FunctionStat"]["Body"]["StatementList"]
        if bodystmts and bodystmts[-1].get("Type") == "ReturnStat" and bodystmts[-1].get("ExprList"):
            retexpr = unwrapexpr(bodystmts[-1]["ExprList"][0])
            if retexpr.get("Type") == "FunctionLiteral":
                wrap = s
                break
    if wrap is None:
        for s in functions:
            if len(s["FunctionStat"].get("ArgList", [])) == 3:
                wrap = s
                break

    retfn = unwrapexpr(wrap["FunctionStat"]["Body"]["StatementList"][-1]["ExprList"][0])
    wbody = retfn["Body"]["StatementList"]

    whilestat = next((s for s in wbody if s.get("Type") == "WhileStat"), None)
    if whilestat is None:
        for s in wbody:
            if s.get("Type") == "LocalFunctionStat":
                innerstmts = s["FunctionStat"]["Body"]["StatementList"]
                whilestat = next((x for x in innerstmts if x.get("Type") == "WhileStat"), None)
                if whilestat is not None:
                    wbody = wbody + innerstmts
                    break

    interpreter = whilestat["Body"]["StatementList"]
    pcountloop = next(s for s in wbody if s.get("Type") == "NumericForStat")

    pcvar = next(
        s["VarList"][0]["Source"]
        for s in wbody
        if s.get("Type") == "LocalVarStat"
        and s.get("ExprList")
        and s["ExprList"][0].get("Type") == "NumberLiteral"
        and s["ExprList"][0]["Token"]["Source"] == "1"
    )
    topvar = next(
        s["VarList"][0]["Source"]
        for s in wbody
        if s.get("Type") == "LocalVarStat"
        and s.get("ExprList")
        and (
            (s["ExprList"][0].get("Type") == "UnopExpr" and s["ExprList"][0]["Rhs"]["Token"]["Source"] == "1")
            or (s["ExprList"][0].get("Type") == "NumberLiteral" and s["ExprList"][0]["Token"]["Source"] == "-1")
        )
    )
    stkvar = pcountloop["Body"]["StatementList"][0]["ElseClauseList"][0]["Body"]["StatementList"][0]["Lhs"][0]["Base"]["Token"]["Source"]

    constvar = None
    if version == "IronBrew V2.7.0":
        firstdef = next(
            (
                s for s in wrap["FunctionStat"]["Body"]["StatementList"]
                if s.get("Type") == "LocalVarStat"
                and s.get("ExprList")
                and s["ExprList"][0].get("Type") == "IndexExpr"
                and s["ExprList"][0]["Index"]["Token"]["Source"] == "2"
            ),
            None,
        )
        if firstdef is not None:
            firstname = firstdef["VarList"][0]["Source"]
            seconddef = next(
                (
                    s for s in wbody
                    if s.get("Type") == "LocalVarStat"
                    and s.get("ExprList")
                    and s["ExprList"][0].get("Type") == "VariableExpr"
                    and s["ExprList"][0]["Variable"]["Name"] == firstname
                ),
                None,
            )
            if seconddef is not None:
                constvar = seconddef["VarList"][0]["Source"]

    unpackvar = "unpack"
    for s in variables:
        if s.get("ExprList"):
            e0 = s["ExprList"][0]
            if (
                e0.get("Type") == "BinopExpr"
                and e0["Rhs"].get("Type") == "FieldExpr"
                and e0["Token_Op"]["Source"] == "or"
            ) or (
                e0.get("Type") == "VariableExpr"
                and e0["Variable"]["Name"].lower() == "unpack"
            ):
                unpackvar = s["VarList"][0]["Source"]
                break

    print(" ok")
    return {
        "Version": version,
        "BytecodeFormat": bformat,
        "ConstantFormat": cformat,
        "Bytecode": bytecode,
        "Tokens": {
            "Clauses": next((s for s in interpreter if s.get("Type") == "IfStat"), None),
            "Top": topvar,
            "Stk": stkvar,
            "Env": wrap["FunctionStat"]["ArgList"][2]["Source"],
            "Wrap": wrap["FunctionStat"]["NameChain"][0]["Source"],
            "Enum": interpreter[1]["Lhs"][0]["Variable"]["Name"],
            "Inst": interpreter[0]["Lhs"][0]["Variable"]["Name"],
            "Const": constvar,
            "Chunk": wrap["FunctionStat"]["ArgList"][0]["Source"],
            "Unpack": unpackvar,
            "Upvalues": wrap["FunctionStat"]["ArgList"][1]["Source"],
            "InstrPoint": pcvar,
        },
        "Keys": {
            "Primary": primary,
            "Secondary": secondary,
            "Tertiary": tertiary,
        },
    }


def parsebytecode(vmstate, flag=True):
    buf = vmstate["Bytecode"]
    bformat = vmstate["BytecodeFormat"]
    cformat = vmstate["ConstantFormat"]
    version = vmstate["Version"]
    pos = 0
    curchunk = 0

    def readu8():
        nonlocal pos
        val = buf[pos]
        pos += 1
        return val

    def readu16():
        nonlocal pos
        val = struct.unpack("<H", buf[pos:pos + 2])[0]
        pos += 2
        return val

    def readu32():
        nonlocal pos
        val = struct.unpack("<I", buf[pos:pos + 4])[0]
        pos += 4
        return val

    def readf64():
        nonlocal pos
        val = struct.unpack("<d", buf[pos:pos + 8])[0]
        pos += 8
        return val

    def readstr(length):
        nonlocal pos
        raw = buf[pos:pos + length]
        pos += length
        return raw.decode("latin1")

    def deserializechunk():
        nonlocal curchunk
        constants = []
        instructions = []
        prototypes = []
        lineinfo = []
        top = (curchunk == 0)
        parameters = 0
        registers = set()
        curchunk += 1

        def addreg(r):
            if r is not None and abs(r) < 256:
                registers.add(abs(r))

        for step in bformat:
            if step == "Constants":
                count = readu32()
                for idx in range(count):
                    t = readu8()
                    if t == cformat.get("Bool"):
                        constants.append(bool(readu8() != 0))
                    elif t == cformat.get("Float"):
                        constants.append(readf64())
                    elif t == cformat.get("String"):
                        slen = readu32()
                        constants.append(readstr(slen))
                    else:
                        constants.append(None)
            elif step == "Instructions":
                count = readu32()
                for idx in range(count):
                    if version == "IronBrew V2.7.0":
                        data1 = bxor(readu32(), vmstate["Keys"]["Secondary"])
                        data2 = bxor(readu32(), vmstate["Keys"]["Tertiary"])
                        itype = gbit(data1, 1, 2)
                        opco = gbit(data2, 1, 11)
                        inst = {
                            "Enum": opco,
                            "Data": data2,
                            "A": gbit(data1, 3, 11),
                            "B": 0,
                            "C": 0,
                        }
                        if itype == 0:
                            inst["B"] = gbit(data1, 12, 20)
                            inst["C"] = gbit(data1, 21, 29)
                        elif itype == 1:
                            inst["B"] = gbit(data2, 12, 33)
                        elif itype == 2:
                            inst["B"] = gbit(data2, 12, 32) - 1048575
                        elif itype == 3:
                            inst["B"] = gbit(data2, 12, 32) - 1048575
                            inst["C"] = gbit(data1, 21, 29)
                        addreg(inst["A"])
                        addreg(inst["B"])
                        addreg(inst["C"])
                        instructions.append(inst)
                    else:
                        descriptor = readu8()
                        if (descriptor & 1) == 0:
                            inst = {
                                "Enum": readu16(),
                                "A": readu16(),
                                "B": 0,
                                "C": 0,
                                "Mask": (descriptor >> 3) & 7,
                            }
                            itype = (descriptor >> 1) & 3
                            if itype == 0:
                                inst["B"] = readu16()
                                inst["C"] = readu16()
                            elif itype == 1:
                                inst["B"] = readu32()
                            elif itype == 2:
                                inst["B"] = readu32() - 65536
                            elif itype == 3:
                                inst["B"] = readu32() - 65536
                                inst["C"] = readu16()
                            addreg(inst["A"])
                            addreg(inst["B"])
                            addreg(inst["C"])
                            instructions.append(inst)
                        else:
                            instructions.append({"Enum": -1, "A": 0, "B": 0, "C": 0, "IsData": True})
            elif step == "Prototypes":
                count = readu32()
                for idx in range(count):
                    prototypes.append(deserializechunk())
            elif step == "Parameters":
                parameters = readu8()
            elif step == "Debug":
                count = readu32()
                for idx in range(count):
                    lineinfo.append(readu32())

        return {
            "Constants": constants,
            "Instructions": instructions,
            "Prototypes": prototypes,
            "Parameters": parameters,
            "Registers": len(registers) + parameters,
            "LineInfo": lineinfo,
            "Top": top,
        }

    topchunk = deserializechunk()
    print(" ok")
    return {
        "Chunk": topchunk,
        "Tokens": vmstate["Tokens"],
        "Version": vmstate["Version"],
    }


def emitcode(vmstate):
    chunk = vmstate["Chunk"] if isinstance(vmstate, dict) and "Chunk" in vmstate else vmstate
    return decompilechunk(chunk)
