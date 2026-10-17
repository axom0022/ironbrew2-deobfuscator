import re
import struct

instructionset = [
    "Move", "LoadK", "LoadBool", "LoadNil", "GetUpval",
    "GetGlobal", "GetTable", "SetGlobal", "SetUpval", "SetTable",
    "NewTable", "Self", "Add", "Sub", "Mul", "Div", "Mod", "Pow",
    "Unm", "Not", "Len", "Concat", "Jmp", "Eq", "Lt", "Le",
    "Test", "TestSet", "Call", "TailCall", "Return", "ForLoop",
    "ForPrep", "TForLoop", "SetList", "Close", "Closure", "VarArg"
]

instructioncategories = [
    "AB",
    "ABx",
    "ABC",
    "AB",
    "AB",
    "ABx",
    "ABC",
    "ABx",
    "AB",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "ABC",
    "AB",
    "AB",
    "AB",
    "ABC",
    "sBx",
    "ABC",
    "ABC",
    "ABC",
    "AC",
    "ABC",
    "ABC",
    "ABC",
    "AB",
    "AsBx",
    "AsBx",
    "AC",
    "ABC",
    "A",
    "ABx",
    "AB"
]

identre = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
luakeywords = frozenset({
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while"
})


def bisectright(sortedlist, target):
    lo = 0
    hi = len(sortedlist)
    while lo < hi:
        mid = (lo + hi) // 2
        if target < sortedlist[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


def isvalidident(s):
    return isinstance(s, str) and bool(identre.match(s)) and s not in luakeywords


def escapeluastr(s):
    if not isinstance(s, str):
        s = str(s)
    out = ['"']
    for ch in s:
        c = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif 32 <= c <= 126:
            out.append(ch)
        else:
            out.append(f"\\{c:03d}")
    out.append('"')
    return "".join(out)


def formatconst(val):
    if val is None:
        return "nil"
    elif isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, (int, float)):
        if isinstance(val, float):
            if val != val:
                return "(0/0)"
            if val == float("inf"):
                return "(1/0)"
            if val == float("-inf"):
                return "(-1/0)"
            if int(val) == val:
                return str(int(val))
        return str(val)
    elif isinstance(val, str):
        return escapeluastr(val)
    return repr(val)


def serializeluac(topchunk):
    buf = bytearray()
    buf.extend(b"\x1bLua")
    buf.extend(bytes([0x51, 0, 1, 4, 4, 4, 8, 0]))

    def writeu8(v):
        buf.append(int(v) & 0xFF)

    def writeu32(v):
        buf.extend(struct.pack("<I", int(v) & 0xFFFFFFFF))

    def writef64(v):
        buf.extend(struct.pack("<d", float(v)))

    def writestr(s):
        raw = s.encode("latin1", errors="replace") + b"\x00"
        writeu32(len(raw))
        buf.extend(raw)

    def masksize(val, bits):
        return int(val) & ((1 << bits) - 1)

    def writechunk(chunk):
        writestr("@deobfuscated" if chunk.get("Top") else "")
        writeu32(0)
        writeu32(0)
        writeu8(chunk.get("Upvalues") or 0)
        writeu8(chunk.get("Parameters") or 0)
        writeu8(3 if chunk.get("VarArg") else 2)

        maxstack = max(2, (chunk.get("Parameters") or 0) + 2)
        for ins in chunk.get("Instructions", []):
            a = ins.get("A") or 0
            b = ins.get("B") or 0
            c = ins.get("C") or 0
            opname = ins.get("OpName", "")
            if a + 2 > maxstack:
                maxstack = a + 2
            if opname not in ("LoadK", "GetGlobal", "SetGlobal", "Closure", "Jmp", "ForLoop", "ForPrep"):
                if 0 <= b < 256 and b + 2 > maxstack:
                    maxstack = b + 2
                if 0 <= c < 256 and c + 2 > maxstack:
                    maxstack = c + 2
            if opname in ("ForLoop", "ForPrep") and a + 5 > maxstack:
                maxstack = a + 5
            elif opname == "TForLoop" and a + 4 + c > maxstack:
                maxstack = a + 4 + c
            elif opname == "Call":
                if b > 1 and a + b + 1 > maxstack:
                    maxstack = a + b + 1
                if c > 1 and a + c > maxstack:
                    maxstack = a + c
        writeu8(min(250, maxstack))

        insts = chunk.get("Instructions", [])
        writeu32(len(insts))
        for ins in insts:
            data = ins["OpCode"]
            itype = ins["Type"]
            a = ins.get("A") or 0
            b = ins.get("B") or 0
            c = ins.get("C") or 0
            if itype == "A":
                data |= masksize(a, 8) << 6
            elif itype == "AB":
                data |= (masksize(a, 8) << 6) | (masksize(b, 9) << 23)
            elif itype == "AC":
                data |= (masksize(a, 8) << 6) | (masksize(c, 9) << 14)
            elif itype == "ABC":
                data |= (masksize(a, 8) << 6) | (masksize(b, 9) << 23) | (masksize(c, 9) << 14)
            elif itype == "ABx":
                data |= (masksize(a, 8) << 6) | (masksize(b, 18) << 14)
            elif itype == "AsBx":
                data |= (masksize(a, 8) << 6) | (masksize(b + 131071, 18) << 14)
            elif itype == "sBx":
                data |= masksize(b + 131071, 18) << 14
            writeu32(data)

        consts = chunk.get("Constants", [])
        writeu32(len(consts))
        for k in consts:
            if k is None:
                writeu8(0)
            elif isinstance(k, bool):
                writeu8(1)
                writeu8(1 if k else 0)
            elif isinstance(k, (int, float)):
                writeu8(3)
                writef64(k)
            elif isinstance(k, str):
                writeu8(4)
                writestr(k)
            else:
                writeu8(0)

        protos = chunk.get("Prototypes", [])
        writeu32(len(protos))
        for p in protos:
            writechunk(p)

        writeu32(0)
        writeu32(0)
        writeu32(0)

    writechunk(topchunk)
    return bytes(buf)


def preprocesschunk(chunk):
    insts = chunk.get("Instructions", [])
    consts = chunk.get("Constants", [])
    protos = chunk.get("Prototypes", [])
    n = len(insts)

    for idx, ins in enumerate(insts):
        ins["PC"] = idx
        ins.pop("_skip", None)
        ins.pop("_jmp_pc", None)
        ins.pop("_target_pc", None)

    pc = 0
    while pc < n:
        ins = insts[pc]
        if ins["OpName"] == "Closure":
            protoidx = ins.get("B") or 0
            nups = ins.get("UpvalueCount", ins.get("C") or 0)
            bindings = []
            actualnups = 0
            for j in range(1, nups + 1):
                if pc + j < n and insts[pc + j]["OpName"] in ("Move", "GetUpval") and (insts[pc + j].get("A") or 0) == 0:
                    sub = insts[pc + j]
                    sub["_skip"] = True
                    bindings.append(("reg" if sub["OpName"] == "Move" else "upval", sub.get("B") or 0))
                    actualnups += 1
                else:
                    break
            if actualnups == 0 and 0 <= protoidx < len(protos):
                pinsts = protos[protoidx].get("Instructions", [])
                maxu = -1
                for pi in pinsts:
                    if pi["OpName"] in ("GetUpval", "SetUpval"):
                        if (pi.get("B") or 0) > maxu:
                            maxu = pi.get("B") or 0
                if maxu >= 0:
                    for j in range(1, maxu + 2):
                        if pc + j < n and insts[pc + j]["OpName"] in ("Move", "GetUpval") and (insts[pc + j].get("A") or 0) == 0:
                            sub = insts[pc + j]
                            sub["_skip"] = True
                            bindings.append(("reg" if sub["OpName"] == "Move" else "upval", sub.get("B") or 0))
                            actualnups += 1
                        else:
                            break
            ins["_upval_bindings"] = bindings
            if 0 <= protoidx < len(protos):
                protos[protoidx]["_upval_bindings"] = bindings
                protos[protoidx]["Upvalues"] = len(bindings)
            pc += actualnups + 1
        else:
            pc += 1

    pc = 0
    while pc < n:
        ins = insts[pc]
        if ins.get("_skip"):
            pc += 1
            continue
        op = ins["OpName"]
        if op in ("Eq", "Lt", "Le", "Test", "TestSet", "TForLoop"):
            if op in ("Eq", "Lt", "Le", "Test") and pc + 2 < n:
                ins1 = insts[pc + 1]
                ins2 = insts[pc + 2]
                if (
                    not ins1.get("_skip")
                    and not ins2.get("_skip")
                    and ins1["OpName"] == "Jmp"
                    and ins1.get("B") == 1
                    and ins2["OpName"] == "Jmp"
                ):
                    if op in ("Eq", "Lt", "Le"):
                        ins["A"] = 0 if ins.get("A") else 1
                    else:
                        ins["C"] = 0 if ins.get("C") else 1
                    ins1["_skip"] = True
                    ins2["_skip"] = True
                    ins["_jmp_pc"] = pc + 2
                    ins["_target_pc"] = (pc + 2) + 1 + (ins2.get("B") or 0)
                    pc += 3
                    continue
            if pc + 1 < n and not insts[pc + 1].get("_skip") and insts[pc + 1]["OpName"] == "Jmp":
                ins1 = insts[pc + 1]
                ins1["_skip"] = True
                ins["_jmp_pc"] = pc + 1
                ins["_target_pc"] = (pc + 1) + 1 + (ins1.get("B") or 0)
                pc += 2
                continue
            elif "_ib2_target" in ins:
                ins["_target_pc"] = ins["_ib2_target"]
        pc += 1

    pc = 0
    while pc + 30 < n:
        ins0 = insts[pc]
        if (
            not ins0.get("_skip")
            and ins0["OpName"] == "LoadK"
            and 0 <= (ins0.get("B") or 0) < len(consts)
            and isinstance(consts[ins0.get("B") or 0], str)
        ):
            renc = ins0.get("A") or 0
            ins1 = insts[pc + 1]
            ins2 = insts[pc + 2]
            ins3 = insts[pc + 3]
            ins4 = insts[pc + 4]
            ins5 = insts[pc + 5]
            if (
                ins1["OpName"] == "Move" and ins1.get("B") == renc
                and ins2["OpName"] == "Move" and ins2.get("A") == ins1.get("A") and ins2.get("B") == ins1.get("A")
                and ins3["OpName"] == "Move" and ins3.get("A") == ins1.get("A") and ins3.get("B") == ins1.get("A")
                and ins4["OpName"] == "Move" and ins4.get("A") == ins1.get("A") and ins4.get("B") == ins1.get("A")
                and ins5["OpName"] == "LoadK" and 0 <= (ins5.get("B") or 0) < len(consts) and consts[ins5.get("B") or 0] == ""
            ):
                if (
                    pc + 26 < n
                    and insts[pc + 20]["OpName"] == "ForLoop"
                    and insts[pc + 21]["OpName"] == "LoadK"
                    and insts[pc + 25]["OpName"] == "ForPrep"
                ):
                    kkey = insts[pc + 21].get("B") or 0
                    forprepins = insts[pc + 25]
                    forlooppc = (pc + 25) + 1 + (forprepins.get("B") or 0)
                    if (
                        0 <= kkey < len(consts)
                        and isinstance(consts[kkey], str)
                        and len(consts[kkey]) > 0
                        and 0 <= forlooppc < n
                        and insts[forlooppc]["OpName"] == "ForLoop"
                        and forlooppc + 4 < n
                        and insts[forlooppc + 1]["OpName"] == "Move"
                        and insts[forlooppc + 4]["OpName"] == "Jmp"
                    ):
                        encs = consts[ins0.get("B") or 0]
                        keys = consts[kkey]
                        klen = len(keys)
                        decs = "".join(chr(ord(encs[i]) ^ ord(keys[i % klen])) for i in range(len(encs)))
                        knew = len(consts)
                        consts.append(decs)
                        rdst = insts[forlooppc + 1].get("A") or 0
                        ins0["A"] = rdst
                        ins0["B"] = knew
                        for skippc in range(pc + 1, forlooppc + 5):
                            insts[skippc]["_skip"] = True
                        pc = forlooppc + 5
                        continue
        pc += 1


def decompilechunk(chunk, indent=0, upvalnames=None):
    preprocesschunk(chunk)
    insts = chunk.get("Instructions", [])
    consts = chunk.get("Constants", [])
    protos = chunk.get("Prototypes", [])
    numparams = chunk.get("Parameters") or 0
    isvararg = bool(chunk.get("VarArg"))
    upvalnames = upvalnames or {}
    n = len(insts)

    jumptargets = set()
    backjumpsto = {}
    branchpcs = []
    for pc, ins in enumerate(insts):
        if ins.get("_skip") or ins.get("CustomOp"):
            continue
        op = ins["OpName"]
        if op in ("Jmp", "ForPrep", "ForLoop", "TForLoop", "Eq", "Lt", "Le", "Test", "TestSet", "Return", "TailCall"):
            istforprepjmp = (
                op == "Jmp"
                and 0 <= pc + 1 + (ins.get("B") or 0) < n
                and insts[pc + 1 + (ins.get("B") or 0)]["OpName"] == "TForLoop"
            )
            if not istforprepjmp:
                branchpcs.append(pc)
        if "_target_pc" in ins:
            jumptargets.add(ins["_target_pc"])
        elif op in ("Jmp", "ForLoop", "ForPrep"):
            t = pc + 1 + (ins.get("B") or 0)
            if op == "ForPrep":
                t += 1
            jumptargets.add(t)
            if op == "Jmp" and t <= pc:
                backjumpsto.setdefault(t, []).append(pc)

    for t in backjumpsto:
        backjumpsto[t].sort(reverse=True)
    sortedjumptargets = sorted(jumptargets)

    regwritecount = {}
    regreadcount = {}
    regwritepcs = {}
    regreadpcs = {}

    def recordwrite(r, pc):
        if r is not None and 0 <= r < 256:
            regwritecount[r] = regwritecount.get(r, 0) + 1
            regwritepcs.setdefault(r, []).append(pc)

    def recordread(r, pc):
        if r is not None and 0 <= r < 256:
            regreadcount[r] = regreadcount.get(r, 0) + 1
            regreadpcs.setdefault(r, []).append(pc)

    for r in range(numparams):
        recordwrite(r, -1)

    lastmultret = 0
    for pc, ins in enumerate(insts):
        if ins.get("_skip"):
            continue
        if ins.get("CustomOp"):
            if ins["CustomOp"] == "SetTop":
                lastmultret = ins.get("OrigA") or 0
            continue
        op = ins["OpName"]
        a = ins.get("A") or 0
        b = ins.get("B") or 0
        c = ins.get("C") or 0
        if op == "Move":
            if a != b:
                recordread(b, pc)
                recordwrite(a, pc)
        elif op in ("LoadK", "LoadBool", "GetUpval", "GetGlobal", "NewTable"):
            recordwrite(a, pc)
        elif op == "LoadNil":
            for r in range(a, b + 1):
                recordwrite(r, pc)
        elif op == "GetTable":
            recordread(b, pc)
            if c < 256:
                recordread(c, pc)
            recordwrite(a, pc)
        elif op in ("SetGlobal", "SetUpval"):
            recordread(a, pc)
        elif op == "SetTable":
            recordread(a, pc)
            if b < 256:
                recordread(b, pc)
            if c < 256:
                recordread(c, pc)
        elif op == "Self":
            recordread(b, pc)
            if c < 256:
                recordread(c, pc)
            recordwrite(a, pc)
            recordwrite(a + 1, pc)
        elif op in ("Add", "Sub", "Mul", "Div", "Mod", "Pow"):
            if b < 256:
                recordread(b, pc)
            if c < 256:
                recordread(c, pc)
            recordwrite(a, pc)
        elif op in ("Unm", "Not", "Len"):
            recordread(b, pc)
            recordwrite(a, pc)
        elif op == "Concat":
            for r in range(b, c + 1):
                recordread(r, pc)
            recordwrite(a, pc)
        elif op in ("Eq", "Lt", "Le"):
            if b < 256:
                recordread(b, pc)
            if c < 256:
                recordread(c, pc)
        elif op == "Test":
            recordread(a, pc)
        elif op == "TestSet":
            recordread(b, pc)
            recordwrite(a, pc)
        elif op in ("Call", "TailCall"):
            recordread(a, pc)
            if b == 0:
                for r in range(a + 1, max(a + 1, lastmultret + 1)):
                    recordread(r, pc)
            elif b > 1:
                for r in range(a + 1, a + b):
                    recordread(r, pc)
            if op == "Call":
                if c == 0:
                    recordwrite(a, pc)
                    lastmultret = a
                elif c == 2:
                    recordwrite(a, pc)
                elif c > 2:
                    for r in range(a, a + c - 1):
                        recordwrite(r, pc)
        elif op == "Return":
            if b == 0:
                for r in range(a, max(a, lastmultret) + 1):
                    recordread(r, pc)
            elif b > 1:
                for r in range(a, a + b - 1):
                    recordread(r, pc)
        elif op == "ForPrep":
            recordread(a, pc)
            recordread(a + 1, pc)
            recordread(a + 2, pc)
            recordwrite(a + 3, pc)
        elif op == "Jmp":
            target = pc + 1 + b
            if 0 <= target < n and insts[target]["OpName"] == "TForLoop":
                tfa = insts[target].get("A") or 0
                recordread(tfa, pc)
                recordread(tfa + 1, pc)
                recordread(tfa + 2, pc)
        elif op == "TForLoop":
            for r in range(a + 3, a + 3 + c):
                recordwrite(r, pc)
        elif op == "SetList":
            recordread(a, pc)
            if b == 0:
                for r in range(a + 1, max(a + 1, lastmultret + 1)):
                    recordread(r, pc)
            elif b > 0:
                for r in range(a + 1, a + b + 1):
                    recordread(r, pc)
        elif op == "Closure":
            for btype, bidx in ins.get("_upval_bindings", []):
                if btype == "reg":
                    recordread(bidx, pc)
                    recordread(bidx, pc)
            recordwrite(a, pc)
        elif op == "VarArg":
            if b == 0:
                recordwrite(a, pc)
                lastmultret = a
            elif b > 1:
                for r in range(a, a + b - 1):
                    recordwrite(r, pc)
            else:
                recordwrite(a, pc)

    persistentlocals = set(range(numparams))

    regnames = {}
    for r in range(numparams):
        regnames[r] = f"p{r + 1}"

    def getvarname(r):
        if r not in regnames:
            regnames[r] = f"v{r}"
        return regnames[r]

    declaredlocals = set(range(numparams))
    regexpr = {r: regnames[r] for r in range(numparams)}
    selfcallinfo = {}
    tablebuilders = {}
    multretreg = [None]

    def hasinrange(sortedlist, loexclusive, hiinclusive):
        idx = bisectright(sortedlist, loexclusive)
        return idx < len(sortedlist) and sortedlist[idx] <= hiinclusive

    def issingleusetemp(r, defpc):
        if r in persistentlocals:
            return False
        wlist = regwritepcs.get(r)
        if wlist:
            widx = bisectright(wlist, defpc)
            nextw = wlist[widx] if widx < len(wlist) else n
        else:
            nextw = n
        rlist = regreadpcs.get(r)
        if not rlist:
            return False
        rstart = bisectright(rlist, defpc)
        rend = bisectright(rlist, nextw)
        if rend - rstart != 1:
            return False
        usepc = rlist[rstart]
        if hasinrange(sortedjumptargets, defpc, usepc):
            return False
        if hasinrange(branchpcs, defpc, usepc - 1):
            return False
        if nextw < n and rend < len(rlist):
            if hasinrange(branchpcs, defpc, nextw - 1):
                return False
        return True

    def needsparensasprefix(exprs):
        return (
            exprs.startswith("{")
            or exprs.startswith('"')
            or exprs.startswith("'")
            or exprs.startswith("function(")
            or exprs.startswith("-")
            or exprs.startswith("not ")
            or exprs.startswith("#")
        )

    def rkexpr(val):
        if val >= 256:
            kidx = val - 256
            if 0 <= kidx < len(consts):
                return formatconst(consts[kidx])
            return "nil"
        return readreg(val)

    def readreg(r):
        if r in tablebuilders:
            entries = tablebuilders.pop(r)
            expr = "{" + ", ".join(entries) + "}"
            regexpr[r] = expr
        return regexpr.get(r, getvarname(r))

    toppredeclared = set()

    def assignreg(r, expr, lines, curindent, forcestmt=False, nextpc=None):
        selfcallinfo.pop(r, None)
        tablebuilders.pop(r, None)
        defpc = (nextpc - 1) if nextpc is not None else -1
        needlocal = forcestmt or (defpc < 0) or (not issingleusetemp(r, defpc))

        if needlocal:
            vname = getvarname(r)
            pad = "    " * curindent
            if r not in declaredlocals:
                declaredlocals.add(r)
                if curindent > indent:
                    toppredeclared.add(vname)
                    lines.append(f"{pad}{vname} = {expr}")
                else:
                    lines.append(f"{pad}local {vname} = {expr}")
            elif vname != expr:
                lines.append(f"{pad}{vname} = {expr}")
            regexpr[r] = vname
        else:
            regexpr[r] = expr

    def buildcondexpr(ins):
        op = ins["OpName"]
        a = ins.get("A") or 0
        b = ins.get("B") or 0
        c = ins.get("C") or 0
        if op == "Eq":
            lhs = rkexpr(b)
            rhs = rkexpr(c)
            return f"{lhs} ~= {rhs}" if a else f"{lhs} == {rhs}"
        elif op == "Lt":
            lhs = rkexpr(b)
            rhs = rkexpr(c)
            return f"{lhs} >= {rhs}" if a else f"{lhs} < {rhs}"
        elif op == "Le":
            lhs = rkexpr(b)
            rhs = rkexpr(c)
            return f"{lhs} > {rhs}" if a else f"{lhs} <= {rhs}"
        elif op == "Test":
            v = readreg(a)
            return f"not {v}" if c else v
        elif op == "TestSet":
            v = readreg(b)
            return f"not {v}" if c else v
        return "true"

    def decompilerange(startpc, endpc, curindent, loopexitpc=None):
        lines = []
        pc = startpc
        pad = "    " * curindent

        while pc < endpc and pc < n:
            ins = insts[pc]
            if ins.get("_skip"):
                pc += 1
                continue
            if ins.get("CustomOp"):
                if ins["CustomOp"] == "SetTop":
                    multretreg[0] = ins.get("OrigA", 0)
                pc += 1
                continue

            op = ins["OpName"]
            a = ins.get("A") or 0
            b = ins.get("B") or 0
            c = ins.get("C") or 0

            backjmppc = None
            if pc in backjumpsto:
                for scanpc in backjumpsto[pc]:
                    if pc < scanpc < endpc and not insts[scanpc].get("_skip"):
                        backjmppc = scanpc
                        break
            if backjmppc is not None:
                sins = insts[backjmppc]
                sins["_skip"] = True
                whileexitpc = backjmppc + 1
                if op in ("Eq", "Lt", "Le", "Test", "TestSet") and ins.get("_target_pc") == whileexitpc:
                    condstr = buildcondexpr(ins)
                    bodystart = (ins.get("_jmp_pc") or pc) + 1
                    lines.append(f"{pad}while {condstr} do")
                    bodylines = decompilerange(bodystart, backjmppc, curindent + 1, loopexitpc=whileexitpc)
                    lines.extend(bodylines)
                    lines.append(f"{pad}end")
                    pc = whileexitpc
                    continue
                else:
                    lines.append(f"{pad}while true do")
                    bodylines = decompilerange(pc, backjmppc, curindent + 1, loopexitpc=whileexitpc)
                    lines.extend(bodylines)
                    lines.append(f"{pad}end")
                    pc = whileexitpc
                    continue

            if op == "Move":
                if a != b:
                    val = readreg(b)
                    assignreg(a, val, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "LoadK":
                val = formatconst(consts[b]) if 0 <= b < len(consts) else "nil"
                assignreg(a, val, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "LoadBool":
                val = "true" if b != 0 else "false"
                assignreg(a, val, lines, curindent, nextpc=pc + 1)
                if c != 0:
                    pc += 2
                else:
                    pc += 1

            elif op == "LoadNil":
                for r in range(a, b + 1):
                    assignreg(r, "nil", lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "GetUpval":
                uname = upvalnames.get(b, f"upval_{b}")
                assignreg(a, uname, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "SetUpval":
                uname = upvalnames.get(b, f"upval_{b}")
                val = readreg(a)
                lines.append(f"{pad}{uname} = {val}")
                pc += 1

            elif op == "GetGlobal":
                gname = consts[b] if 0 <= b < len(consts) else f"_G[{b}]"
                if not isvalidident(gname):
                    gname = f"_G[{formatconst(gname)}]"
                assignreg(a, gname, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "SetGlobal":
                gname = consts[b] if 0 <= b < len(consts) else f"_G[{b}]"
                val = readreg(a)
                if isvalidident(gname):
                    lines.append(f"{pad}{gname} = {val}")
                else:
                    lines.append(f"{pad}_G[{formatconst(gname)}] = {val}")
                pc += 1

            elif op == "NewTable":
                wlist = regwritepcs.get(a)
                if wlist:
                    widx = bisectright(wlist, pc)
                    nextw = wlist[widx] if widx < len(wlist) else n
                else:
                    nextw = n
                rlist = regreadpcs.get(a, [])
                rstart = bisectright(rlist, pc)
                rend = bisectright(rlist, nextw)
                noninitreads = [
                    rlist[k] for k in range(rstart, rend)
                    if not (insts[rlist[k]]["OpName"] in ("SetTable", "SetList") and (insts[rlist[k]].get("A") or 0) == a)
                ]
                if a not in persistentlocals and len(noninitreads) == 1:
                    tablebuilders[a] = []
                    regexpr[a] = "{}"
                else:
                    assignreg(a, "{}", lines, curindent, forcestmt=True, nextpc=pc + 1)
                pc += 1

            elif op == "GetTable":
                tbl = readreg(b)
                if needsparensasprefix(tbl):
                    tbl = f"({tbl})"
                if c >= 256 and 0 <= (c - 256) < len(consts) and isvalidident(consts[c - 256]):
                    expr = f"{tbl}.{consts[c - 256]}"
                else:
                    idx = rkexpr(c)
                    expr = f"{tbl}[{idx}]"
                assignreg(a, expr, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "SetTable":
                val = rkexpr(c)
                if a in tablebuilders:
                    if b >= 256 and 0 <= (b - 256) < len(consts) and isvalidident(consts[b - 256]):
                        tablebuilders[a].append(f"{consts[b - 256]} = {val}")
                    else:
                        idx = rkexpr(b)
                        tablebuilders[a].append(f"[{idx}] = {val}")
                else:
                    tbl = readreg(a)
                    lead = ""
                    if needsparensasprefix(tbl):
                        tbl = f"({tbl})"
                        lead = ";"
                    elif tbl.startswith("("):
                        lead = ";"
                    if b >= 256 and 0 <= (b - 256) < len(consts) and isvalidident(consts[b - 256]):
                        lines.append(f"{pad}{lead}{tbl}.{consts[b - 256]} = {val}")
                    else:
                        idx = rkexpr(b)
                        lines.append(f"{pad}{lead}{tbl}[{idx}] = {val}")
                pc += 1

            elif op == "SetList":
                if b == 0:
                    topr = multretreg[0] if multretreg[0] is not None else a + 1
                    items = [readreg(r) for r in range(a + 1, topr + 1)]
                else:
                    items = [readreg(r) for r in range(a + 1, a + b + 1)]
                if a in tablebuilders:
                    tablebuilders[a].extend(items)
                else:
                    tbl = readreg(a)
                    for item in items:
                        lines.append(f"{pad}table.insert({tbl}, {item})")
                pc += 1

            elif op == "Self":
                obj = readreg(b)
                if needsparensasprefix(obj):
                    obj = f"({obj})"
                if c >= 256 and 0 <= (c - 256) < len(consts) and isvalidident(consts[c - 256]):
                    mname = consts[c - 256]
                    selfcallinfo[a] = (obj, mname)
                    regexpr[a + 1] = obj
                    regexpr[a] = f"{obj}.{mname}"
                else:
                    idx = rkexpr(c)
                    regexpr[a + 1] = obj
                    regexpr[a] = f"{obj}[{idx}]"
                pc += 1

            elif op in ("Add", "Sub", "Mul", "Div", "Mod", "Pow"):
                sym = {"Add": "+", "Sub": "-", "Mul": "*", "Div": "/", "Mod": "%", "Pow": "^"}[op]
                lhs = rkexpr(b)
                rhs = rkexpr(c)
                assignreg(a, f"({lhs} {sym} {rhs})", lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op in ("Unm", "Not", "Len"):
                rhs = readreg(b)
                if op == "Unm":
                    expr = f"-{rhs}"
                elif op == "Not":
                    expr = f"not {rhs}"
                else:
                    expr = f"#{rhs}"
                assignreg(a, expr, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "Concat":
                parts = [readreg(r) for r in range(b, c + 1)]
                assignreg(a, " .. ".join(parts), lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op in ("Call", "TailCall"):
                ismethod = a in selfcallinfo
                if ismethod:
                    objexpr, mname = selfcallinfo.pop(a)
                    fnstr = f"{objexpr}:{mname}"
                    argstart = a + 2
                else:
                    fnstr = readreg(a)
                    if fnstr.startswith("function(") or fnstr.startswith("{") or fnstr.startswith('"'):
                        fnstr = f"({fnstr})"
                    argstart = a + 1

                if b == 0:
                    topr = multretreg[0] if (multretreg[0] is not None and multretreg[0] >= argstart) else argstart
                    args = [readreg(r) for r in range(argstart, topr + 1)]
                elif b == 1:
                    args = []
                else:
                    args = [readreg(r) for r in range(argstart, a + b)]

                callstr = f"{fnstr}({', '.join(args)})"

                if op == "TailCall":
                    if pc + 1 < n and insts[pc + 1]["OpName"] == "Return":
                        insts[pc + 1]["_skip"] = True
                    hasmore = any(not insts[k].get("_skip") for k in range(pc + 1, min(endpc, n)))
                    if hasmore:
                        lines.append(f"{pad}do return {callstr} end")
                    else:
                        lines.append(f"{pad}return {callstr}")
                elif c == 1:
                    lead = ";" if callstr.startswith("(") else ""
                    lines.append(f"{pad}{lead}{callstr}")
                elif c == 0:
                    regexpr[a] = callstr
                    multretreg[0] = a
                elif c == 2:
                    assignreg(a, callstr, lines, curindent, nextpc=pc + 1)
                elif (
                    c == 4
                    and pc + 1 < n
                    and insts[pc + 1]["OpName"] == "Jmp"
                    and 0 <= (pc + 1) + 1 + (insts[pc + 1].get("B") or 0) < n
                    and insts[(pc + 1) + 1 + (insts[pc + 1].get("B") or 0)]["OpName"] == "TForLoop"
                    and (insts[(pc + 1) + 1 + (insts[pc + 1].get("B") or 0)].get("A") or 0) == a
                ):
                    regexpr[a] = callstr
                    regexpr[a + 1] = None
                    regexpr[a + 2] = None
                else:
                    lhsvars = []
                    newdecl = False
                    for r in range(a, a + c - 1):
                        vname = getvarname(r)
                        if r not in declaredlocals:
                            declaredlocals.add(r)
                            if curindent > indent:
                                toppredeclared.add(vname)
                            else:
                                newdecl = True
                        regexpr[r] = vname
                        lhsvars.append(vname)
                    prefix = "local " if newdecl else ""
                    lines.append(f"{pad}{prefix}{', '.join(lhsvars)} = {callstr}")
                pc += 1

            elif op == "Return":
                if b == 1 and pc == n - 1:
                    pc += 1
                    continue
                if pc + 1 < n and insts[pc + 1]["OpName"] == "Return" and (insts[pc + 1].get("B") or 0) == 1:
                    insts[pc + 1]["_skip"] = True
                if b == 0:
                    topr = multretreg[0] if (multretreg[0] is not None and multretreg[0] >= a) else a
                    vals = [readreg(r) for r in range(a, topr + 1)]
                elif b == 1:
                    vals = []
                else:
                    vals = [readreg(r) for r in range(a, a + b - 1)]
                hasmore = any(not insts[k].get("_skip") for k in range(pc + 1, min(endpc, n)))
                retstmt = f"return {', '.join(vals)}" if vals else "return"
                if hasmore:
                    lines.append(f"{pad}do {retstmt} end")
                else:
                    lines.append(f"{pad}{retstmt}")
                pc += 1

            elif op == "VarArg":
                if b == 0:
                    regexpr[a] = "..."
                    multretreg[0] = a
                elif b == 2:
                    assignreg(a, "...", lines, curindent, nextpc=pc + 1)
                elif b > 2:
                    lhsvars = []
                    for r in range(a, a + b - 1):
                        vname = getvarname(r)
                        declaredlocals.add(r)
                        regexpr[r] = vname
                        lhsvars.append(vname)
                    lines.append(f"{pad}local {', '.join(lhsvars)} = ...")
                pc += 1

            elif op == "Closure":
                if 0 <= b < len(protos):
                    proto = protos[b]
                    childupvals = {}
                    for uidx, (btype, bidx) in enumerate(ins.get("_upval_bindings", [])):
                        if btype == "reg":
                            childupvals[uidx] = readreg(bidx)
                        else:
                            childupvals[uidx] = upvalnames.get(bidx, f"upval_{bidx}")
                    pparams = [f"p{i + 1}" for i in range(proto.get("Parameters") or 0)]
                    if proto.get("VarArg"):
                        pparams.append("...")
                    bodystr = decompilechunk(proto, curindent + 1, childupvals)
                    if bodystr.strip():
                        fnexpr = f"function({', '.join(pparams)})\n{bodystr}\n{pad}end"
                    else:
                        fnexpr = f"function({', '.join(pparams)}) end"
                else:
                    fnexpr = "function() end"
                assignreg(a, fnexpr, lines, curindent, nextpc=pc + 1)
                pc += 1

            elif op == "ForPrep":
                startv = readreg(a)
                limitv = readreg(a + 1)
                stepv = readreg(a + 2)
                forlooppc = pc + 1 + b + 1
                loopvar = f"i_{a + 3}"
                regnames[a + 3] = loopvar
                declaredlocals.add(a + 3)
                regexpr[a + 3] = loopvar
                steppart = "" if stepv == "1" else f", {stepv}"
                lines.append(f"{pad}for {loopvar} = {startv}, {limitv}{steppart} do")
                if pc + 1 <= forlooppc < n:
                    insts[forlooppc]["_skip"] = True
                    bodylines = decompilerange(pc + 1, forlooppc, curindent + 1, loopexitpc=forlooppc + 1)
                    lines.extend(bodylines)
                    pc = forlooppc + 1
                else:
                    pc += 1
                lines.append(f"{pad}end")

            elif op == "Jmp":
                target = pc + 1 + b
                if pc < target < endpc and target < n and insts[target]["OpName"] == "TForLoop":
                    tforins = insts[target]
                    tfa = tforins.get("A") or 0
                    tfc = tforins.get("C") or 1
                    if regexpr.get(tfa + 1) is None and regexpr.get(tfa + 2) is None:
                        iterstr = readreg(tfa)
                    else:
                        g0 = readreg(tfa)
                        g1 = readreg(tfa + 1)
                        g2 = readreg(tfa + 2)
                        if g2 == "nil":
                            iterstr = f"{g0}, {g1}"
                        else:
                            iterstr = f"{g0}, {g1}, {g2}"
                    loopvars = []
                    for idxv in range(tfc):
                        rv = tfa + 3 + idxv
                        vname = f"k_{rv}" if idxv == 0 else f"v_{rv}"
                        regnames[rv] = vname
                        declaredlocals.add(rv)
                        regexpr[rv] = vname
                        loopvars.append(vname)
                    lines.append(f"{pad}for {', '.join(loopvars)} in {iterstr} do")
                    tforins["_skip"] = True
                    nextaftertfor = (tforins.get("_jmp_pc") or target) + 1
                    bodylines = decompilerange(pc + 1, target, curindent + 1, loopexitpc=nextaftertfor)
                    lines.extend(bodylines)
                    lines.append(f"{pad}end")
                    pc = nextaftertfor
                    continue
                elif loopexitpc is not None and target == loopexitpc:
                    hasmore = any(not insts[k].get("_skip") for k in range(pc + 1, min(endpc, n)))
                    lines.append(f"{pad}do break end" if hasmore else f"{pad}break")
                pc += 1

            elif op in ("Eq", "Lt", "Le", "Test", "TestSet"):
                condstr = buildcondexpr(ins)
                thenstart = (ins.get("_jmp_pc") or pc) + 1
                falsetarget = ins.get("_target_pc", thenstart)

                if (
                    falsetarget == thenstart + 1
                    and thenstart + 1 < n
                    and insts[thenstart]["OpName"] == "LoadBool"
                    and insts[thenstart].get("C") == 1
                    and insts[thenstart + 1]["OpName"] == "LoadBool"
                    and insts[thenstart].get("A") == insts[thenstart + 1].get("A")
                ):
                    dstr = insts[thenstart].get("A") or 0
                    assignreg(dstr, f"({condstr})", lines, curindent, nextpc=thenstart + 2)
                    pc = thenstart + 2
                    continue

                if loopexitpc is not None and falsetarget == loopexitpc:
                    lines.append(f"{pad}if not ({condstr}) then")
                    lines.append(f"{pad}    break")
                    lines.append(f"{pad}end")
                    pc = thenstart
                    continue

                if thenstart < falsetarget:
                    if falsetarget <= endpc:
                        lastthenins = insts[falsetarget - 1]
                        if (
                            not lastthenins.get("_skip")
                            and lastthenins["OpName"] == "Jmp"
                            and (falsetarget - 1) + 1 + (lastthenins.get("B") or 0) >= falsetarget
                        ):
                            endifpc = (falsetarget - 1) + 1 + (lastthenins.get("B") or 0)
                            if loopexitpc is not None and endifpc == loopexitpc and falsetarget == thenstart + 1:
                                lines.append(f"{pad}if {condstr} then")
                                lines.append(f"{pad}    break")
                                lines.append(f"{pad}end")
                                pc = falsetarget
                                continue
                            lastthenins["_skip"] = True
                            lines.append(f"{pad}if {condstr} then")
                            thenlines = decompilerange(thenstart, falsetarget - 1, curindent + 1, loopexitpc=loopexitpc)
                            lines.extend(thenlines)
                            if falsetarget < min(endifpc, endpc):
                                lines.append(f"{pad}else")
                                elselines = decompilerange(falsetarget, min(endifpc, endpc), curindent + 1, loopexitpc=loopexitpc)
                                lines.extend(elselines)
                            lines.append(f"{pad}end")
                            pc = max(falsetarget, min(endifpc, endpc))
                            continue
                        else:
                            lines.append(f"{pad}if {condstr} then")
                            thenlines = decompilerange(thenstart, falsetarget, curindent + 1, loopexitpc=loopexitpc)
                            lines.extend(thenlines)
                            lines.append(f"{pad}end")
                            pc = falsetarget
                            continue
                    else:
                        lines.append(f"{pad}if {condstr} then")
                        thenlines = decompilerange(thenstart, endpc, curindent + 1, loopexitpc=loopexitpc)
                        lines.extend(thenlines)
                        lines.append(f"{pad}end")
                        pc = endpc
                        continue
                pc = thenstart

            else:
                pc += 1

        return lines

    outlines = decompilerange(0, n, indent)
    if toppredeclared:
        pad = "    " * indent
        prevars = ", ".join(sorted(toppredeclared, key=lambda x: int(x[1:]) if x[1:].isdigit() else 999))
        outlines.insert(0, f"{pad}local {prevars}")
    return "\n".join(outlines)
