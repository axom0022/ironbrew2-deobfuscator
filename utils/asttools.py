import re

tokenre = re.compile(
    r"""
    (?P<WS>\s+)
  | (?P<LONGCOMMENT>--\[(?P<lceq>=*)\[[\s\S]*?\](?P=lceq)\])
  | (?P<COMMENT>--[^\r\n]*)
  | (?P<LONGSTRING>\[(?P<lseq>=*)\[(?P<lsbody>[\s\S]*?)\](?P=lseq)\])
  | (?P<STRING>'(?:\\[\s\S]|[^'\\\r\n])*'|"(?:\\[\s\S]|[^"\\\r\n])*")
  | (?P<HEX>0[xX][0-9a-fA-F]+)
  | (?P<NUMBER>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
  | (?P<DOTS>\.\.\.)
  | (?P<CONCAT>\.\.)
  | (?P<OP2>==|~=|<=|>=|\+=|-=|\*=|/=|%=|\.\.=)
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<SYM>[+\-*/%^#<>=\(\)\{\}\[\];:,\\.])
    """,
    64,
)

keywords = frozenset({
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while"
})

binopprec = {
    "or": (1, 1),
    "and": (2, 2),
    "<": (3, 3), ">": (3, 3), "<=": (3, 3), ">=": (3, 3), "~=": (3, 3), "==": (3, 3),
    "..": (4, 3),
    "+": (5, 5), "-": (5, 5),
    "*": (6, 6), "/": (6, 6), "%": (6, 6),
    "^": (8, 7),
}

unops = frozenset({"not", "#", "-"})


def tokenize(source):
    tokens = []
    for m in tokenre.finditer(source):
        kind = m.lastgroup
        if kind in ("WS", "COMMENT", "LONGCOMMENT"):
            continue
        val = m.group()
        if kind == "IDENT":
            if val in keywords:
                tokens.append(("KW", val))
            else:
                tokens.append(("IDENT", val))
        elif kind in ("HEX", "NUMBER"):
            tokens.append(("NUMBER", val))
        elif kind == "STRING":
            tokens.append(("STRING", val[1:-1]))
        elif kind == "LONGSTRING":
            tokens.append(("STRING", m.group("lsbody")))
        elif kind == "DOTS":
            tokens.append(("SYM", "..."))
        elif kind == "CONCAT":
            tokens.append(("SYM", ".."))
        elif kind in ("OP2", "SYM"):
            tokens.append(("SYM", val))
    tokens.append(("EOF", ""))
    return tokens


def maketoken(typ, src):
    return {"Type": typ, "LeadingWhite": "", "Source": str(src)}


def loadast(script):
    try:
        tokens = tokenize(script)
        pos = 0
        n = len(tokens)

        def peek():
            return tokens[pos]

        def nexttok():
            nonlocal pos
            tok = tokens[pos]
            pos += 1
            return tok

        def matchtok(kind, val=None):
            nonlocal pos
            tok = tokens[pos]
            if tok[0] == kind and (val is None or tok[1] == val):
                pos += 1
                return tok
            return None

        def expect(kind, val=None):
            nonlocal pos
            tok = tokens[pos]
            if tok[0] == kind and (val is None or tok[1] == val):
                pos += 1
                return tok
            raise RuntimeError(f"Expected {kind} {val!r}, got {tok!r} at token {pos}")

        def isblockend():
            kind, val = tokens[pos]
            if kind == "EOF":
                return True
            if kind == "KW" and val in ("end", "else", "elseif", "until"):
                return True
            return False

        def parseblock():
            stmts = []
            while not isblockend():
                while matchtok("SYM", ";"):
                    pass
                if isblockend():
                    break
                stmt = parsestat()
                if stmt is not None:
                    stmts.append(stmt)
                while matchtok("SYM", ";"):
                    pass
                if stmt is not None and stmt["Type"] in ("ReturnStat", "BreakStat"):
                    break
            return stmts

        def parsestat():
            kind, val = tokens[pos]
            if kind == "KW":
                if val == "local":
                    return parselocal()
                elif val == "if":
                    return parseif()
                elif val == "while":
                    return parsewhile()
                elif val == "repeat":
                    return parserepeat()
                elif val == "for":
                    return parsefor()
                elif val == "function":
                    return parsefuncstat()
                elif val == "do":
                    return parsedo()
                elif val == "return":
                    return parsereturn()
                elif val == "break":
                    nexttok()
                    return {"Type": "BreakStat"}
            return parseexprorassignstat()

        def parselocal():
            expect("KW", "local")
            if matchtok("KW", "function"):
                nametok = expect("IDENT")
                params, body = parsefuncbody()
                fnstat = {
                    "Type": "FunctionStat",
                    "NameChain": [maketoken("Ident", nametok[1])],
                    "ArgList": params,
                    "Body": body,
                }
                return {
                    "Type": "LocalFunctionStat",
                    "FunctionStat": fnstat,
                }
            varlist = []
            first = expect("IDENT")
            varlist.append({"Type": "Ident", "Source": first[1], "Name": first[1]})
            while matchtok("SYM", ","):
                ident = expect("IDENT")
                varlist.append({"Type": "Ident", "Source": ident[1], "Name": ident[1]})
            exprlist = []
            if matchtok("SYM", "="):
                exprlist = parseexprlist()
            return {
                "Type": "LocalVarStat",
                "VarList": varlist,
                "ExprList": exprlist,
            }

        def parsefuncstat():
            expect("KW", "function")
            namechain = []
            first = expect("IDENT")
            namechain.append(maketoken("Ident", first[1]))
            while matchtok("SYM", ".") or matchtok("SYM", ":"):
                part = expect("IDENT")
                namechain.append(maketoken("Ident", part[1]))
            params, body = parsefuncbody()
            return {
                "Type": "FunctionStat",
                "Name": {"Type": "VariableExpr", "Variable": {"Name": first[1]}, "Token": maketoken("Ident", first[1])},
                "NameChain": namechain,
                "Parameters": params,
                "ArgList": params,
                "Body": body,
            }

        def parsefuncbody():
            expect("SYM", "(")
            params = []
            if not matchtok("SYM", ")"):
                while True:
                    if matchtok("SYM", "..."):
                        params.append(maketoken("Symbol", "..."))
                        break
                    ident = expect("IDENT")
                    params.append(maketoken("Ident", ident[1]))
                    if not matchtok("SYM", ","):
                        break
                expect("SYM", ")")
            bodystmts = parseblock()
            expect("KW", "end")
            return params, {"Type": "StatList", "StatementList": bodystmts}

        def parseif():
            expect("KW", "if")
            cond = parseexpr()
            expect("KW", "then")
            thenbody = parseblock()
            elseclauses = []
            while matchtok("KW", "elseif"):
                econd = parseexpr()
                expect("KW", "then")
                ebody = parseblock()
                elseclauses.append({
                    "ClauseType": "elseif",
                    "Condition": econd,
                    "Body": {"StatementList": ebody},
                })
            if matchtok("KW", "else"):
                ebody = parseblock()
                elseclauses.append({
                    "ClauseType": "else",
                    "Condition": None,
                    "Body": {"StatementList": ebody},
                })
            expect("KW", "end")
            return {
                "Type": "IfStat",
                "Condition": cond,
                "Body": {"StatementList": thenbody},
                "ElseClauseList": elseclauses,
            }

        def parsewhile():
            expect("KW", "while")
            cond = parseexpr()
            expect("KW", "do")
            body = parseblock()
            expect("KW", "end")
            return {
                "Type": "WhileStat",
                "Condition": cond,
                "Body": {"StatementList": body},
            }

        def parserepeat():
            expect("KW", "repeat")
            body = parseblock()
            expect("KW", "until")
            cond = parseexpr()
            return {
                "Type": "RepeatStat",
                "Condition": cond,
                "Body": {"StatementList": body},
            }

        def parsedo():
            expect("KW", "do")
            body = parseblock()
            expect("KW", "end")
            return {
                "Type": "DoStat",
                "Body": {"StatementList": body},
            }

        def parsefor():
            expect("KW", "for")
            first = expect("IDENT")
            if matchtok("SYM", "="):
                start = parseexpr()
                expect("SYM", ",")
                end = parseexpr()
                rangelist = [start, end]
                if matchtok("SYM", ","):
                    rangelist.append(parseexpr())
                expect("KW", "do")
                body = parseblock()
                expect("KW", "end")
                vartok = {"Source": first[1], "Name": first[1]}
                return {
                    "Type": "NumericForStat",
                    "VarList": [vartok],
                    "Variable": {"Type": "VariableExpr", "Variable": {"Name": first[1]}, "Token": maketoken("Ident", first[1])},
                    "RangeList": rangelist,
                    "Body": {"StatementList": body},
                }
            else:
                varlist = [{"Source": first[1], "Name": first[1]}]
                while matchtok("SYM", ","):
                    ident = expect("IDENT")
                    varlist.append({"Source": ident[1], "Name": ident[1]})
                expect("KW", "in")
                exprlist = parseexprlist()
                expect("KW", "do")
                body = parseblock()
                expect("KW", "end")
                return {
                    "Type": "GenericForStat",
                    "VarList": varlist,
                    "Names": [{"Type": "VariableExpr", "Variable": {"Name": v["Name"]}, "Token": maketoken("Ident", v["Name"])} for v in varlist],
                    "GeneratorList": exprlist,
                    "ExprList": exprlist,
                    "Body": {"StatementList": body},
                }

        def parsereturn():
            expect("KW", "return")
            exprlist = []
            if not isblockend() and peek() != ("SYM", ";"):
                exprlist = parseexprlist()
            return {
                "Type": "ReturnStat",
                "ExprList": exprlist,
            }

        def parseexprorassignstat():
            first = parseprefixexpr()
            if first["Type"] == "CallExpr":
                return {
                    "Type": "CallExprStat",
                    "Expression": first,
                }
            lhs = [first]
            while matchtok("SYM", ","):
                lhs.append(parseprefixexpr())
            tok = peek()
            if tok[0] == "SYM" and tok[1] in ("+=", "-=", "*=", "/=", "%=", "..="):
                op = nexttok()[1][:-1]
                rhsval = parseexpr()
                binop = {
                    "Type": "BinopExpr",
                    "Lhs": first,
                    "Rhs": rhsval,
                    "Token_Op": maketoken("Symbol", op),
                }
                return {
                    "Type": "AssignmentStat",
                    "Lhs": lhs,
                    "Rhs": [binop],
                }
            expect("SYM", "=")
            rhs = parseexprlist()
            return {
                "Type": "AssignmentStat",
                "Lhs": lhs,
                "Rhs": rhs,
            }

        def parseexprlist():
            exprs = [parseexpr()]
            while matchtok("SYM", ","):
                exprs.append(parseexpr())
            return exprs

        def parseexpr(minprec=1):
            kind, val = tokens[pos]
            if (kind in ("KW", "SYM")) and val in unops:
                nexttok()
                rhs = parseexpr(7)
                lhs = {
                    "Type": "UnopExpr",
                    "Rhs": rhs,
                    "Token_Op": maketoken("Symbol", val),
                }
            else:
                lhs = parsesimpleexpr()

            while True:
                kind, val = tokens[pos]
                if (kind in ("KW", "SYM")) and val in binopprec:
                    lprec, rprec = binopprec[val]
                    if lprec < minprec:
                        break
                    nexttok()
                    rhs = parseexpr(rprec + 1 if lprec == rprec else rprec)
                    lhs = {
                        "Type": "BinopExpr",
                        "Lhs": lhs,
                        "Rhs": rhs,
                        "Token_Op": maketoken("Symbol", val),
                    }
                else:
                    break
            return lhs

        def parsesimpleexpr():
            kind, val = tokens[pos]
            if kind == "NUMBER":
                nexttok()
                return {
                    "Type": "NumberLiteral",
                    "Source": val,
                    "Token": maketoken("Number", val),
                }
            elif kind == "STRING":
                nexttok()
                return {
                    "Type": "StringLiteral",
                    "Source": val,
                    "Token": maketoken("String", val),
                }
            elif kind == "KW":
                if val == "nil":
                    nexttok()
                    return {"Type": "NilLiteral", "Token": maketoken("Keyword", "nil")}
                elif val in ("true", "false"):
                    nexttok()
                    return {
                        "Type": "BooleanLiteral",
                        "Source": val,
                        "Token": maketoken("Boolean", val),
                    }
                elif val == "function":
                    nexttok()
                    params, body = parsefuncbody()
                    return {
                        "Type": "FunctionLiteral",
                        "ArgList": params,
                        "Parameters": params,
                        "Body": body,
                    }
            elif kind == "SYM":
                if val == "...":
                    nexttok()
                    return {"Type": "DotsExpr", "Token": maketoken("Symbol", "...")}
                elif val == "{":
                    return parsetable()
            return parseprefixexpr()

        def parseprefixexpr():
            kind, val = tokens[pos]
            if kind == "IDENT":
                nexttok()
                base = {
                    "Type": "VariableExpr",
                    "Variable": {"Name": val, "Type": "Global"},
                    "Token": maketoken("Ident", val),
                }
            elif kind == "SYM" and val == "(":
                nexttok()
                inner = parseexpr()
                expect("SYM", ")")
                base = {
                    "Type": "ParenExpr",
                    "Expression": inner,
                }
            else:
                raise RuntimeError(f"Unexpected token {peek()!r} at {pos}")

            while True:
                kind, val = tokens[pos]
                if kind == "SYM":
                    if val == ".":
                        nexttok()
                        fieldtok = expect("IDENT")
                        base = {
                            "Type": "FieldExpr",
                            "Base": base,
                            "Field": maketoken("Ident", fieldtok[1]),
                        }
                    elif val == "[":
                        nexttok()
                        idx = parseexpr()
                        expect("SYM", "]")
                        base = {
                            "Type": "IndexExpr",
                            "Base": base,
                            "Index": idx,
                        }
                    elif val == ":":
                        nexttok()
                        methodtok = expect("IDENT")
                        methodbase = {
                            "Type": "MethodExpr",
                            "Base": base,
                            "Method": maketoken("Ident", methodtok[1]),
                        }
                        args = parsecallargs()
                        base = {
                            "Type": "CallExpr",
                            "Base": methodbase,
                            "FunctionArguments": args,
                        }
                    elif val in ("(", "{"):
                        args = parsecallargs()
                        base = {
                            "Type": "CallExpr",
                            "Base": base,
                            "FunctionArguments": args,
                        }
                    else:
                        break
                elif kind == "STRING":
                    args = parsecallargs()
                    base = {
                        "Type": "CallExpr",
                        "Base": base,
                        "FunctionArguments": args,
                    }
                else:
                    break
            return base

        def parsecallargs():
            kind, val = tokens[pos]
            if kind == "SYM" and val == "(":
                nexttok()
                arglist = []
                if not matchtok("SYM", ")"):
                    arglist = parseexprlist()
                    expect("SYM", ")")
                return {"CallType": "ArgCall", "ArgList": arglist}
            elif kind == "SYM" and val == "{":
                tbl = parsetable()
                return {"CallType": "TableCall", "ArgList": [tbl], "TableExpr": tbl}
            elif kind == "STRING":
                nexttok()
                slit = {
                    "Type": "StringLiteral",
                    "Source": val,
                    "Token": maketoken("String", val),
                }
                return {"CallType": "StringCall", "ArgList": [slit], "StringExpr": slit}
            raise RuntimeError(f"Expected call args, got {peek()!r}")

        def parsetable():
            expect("SYM", "{")
            entries = []
            while not matchtok("SYM", "}"):
                kind, val = tokens[pos]
                if kind == "SYM" and val == "[":
                    nexttok()
                    k = parseexpr()
                    expect("SYM", "]")
                    expect("SYM", "=")
                    v = parseexpr()
                    entries.append({"EntryType": "Index", "Key": k, "Value": v})
                elif kind == "IDENT" and pos + 1 < n and tokens[pos + 1] == ("SYM", "="):
                    fname = nexttok()[1]
                    nexttok()
                    v = parseexpr()
                    entries.append({
                        "EntryType": "Field",
                        "Field": maketoken("Ident", fname),
                        "Key": {"Type": "StringLiteral", "Source": fname, "Token": maketoken("String", fname)},
                        "Value": v,
                    })
                else:
                    v = parseexpr()
                    entries.append({"EntryType": "Value", "Key": None, "Value": v})
                if not (matchtok("SYM", ",") or matchtok("SYM", ";")):
                    expect("SYM", "}")
                    break
            return {
                "Type": "TableLiteral",
                "EntryList": entries,
                "Fields": entries,
            }

        stmts = parseblock()
        return {"Type": "Chunk", "StatementList": stmts}
    except Exception as e:
        raise RuntimeError(f"Parse error: {e}")


def refineast(ast, options=None):
    options = options or {}
    if options.get("renamevariables") or options.get("RenameVariables"):
        counter = 0
        scopes = [{}]

        def allocname():
            nonlocal counter
            counter += 1
            return f"v{counter}"

        def lookup(name):
            for s in reversed(scopes):
                if name in s:
                    return s[name]
            return None

        def visitexpr(node):
            if node is None or not isinstance(node, dict):
                return
            typ = node.get("Type")
            if typ == "VariableExpr":
                orig = node["Variable"]["Name"]
                mapped = lookup(orig)
                if mapped is not None:
                    node["Variable"]["Name"] = mapped
                    node["Variable"]["Type"] = "Local"
                    node["Token"]["Source"] = mapped
                else:
                    node["Variable"]["Name"] = orig
                    node["Variable"]["Type"] = "Global"
                    node["Token"]["Source"] = orig
            elif typ == "BinopExpr":
                visitexpr(node["Lhs"])
                visitexpr(node["Rhs"])
            elif typ == "UnopExpr":
                visitexpr(node["Rhs"])
            elif typ == "ParenExpr":
                visitexpr(node["Expression"])
            elif typ == "IndexExpr":
                visitexpr(node["Base"])
                visitexpr(node["Index"])
            elif typ in ("FieldExpr", "MethodExpr"):
                visitexpr(node["Base"])
            elif typ == "CallExpr":
                visitexpr(node["Base"])
                for a in node["FunctionArguments"].get("ArgList", []):
                    visitexpr(a)
            elif typ == "TableLiteral":
                for e in node.get("EntryList", []):
                    if e.get("EntryType") == "Index":
                        visitexpr(e.get("Key"))
                    visitexpr(e.get("Value"))
            elif typ == "FunctionLiteral":
                scopes.append({})
                for p in node.get("ArgList", []):
                    if p["Source"] != "...":
                        newp = allocname()
                        scopes[-1][p["Source"]] = newp
                        p["Source"] = newp
                for s in node["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()

        def visitstat(stat):
            if stat is None or not isinstance(stat, dict):
                return
            typ = stat.get("Type")
            if typ == "LocalVarStat":
                for e in stat.get("ExprList", []):
                    visitexpr(e)
                for v in stat.get("VarList", []):
                    orig = v["Source"]
                    newv = allocname()
                    scopes[-1][orig] = newv
                    v["Source"] = newv
                    v["Name"] = newv
            elif typ == "LocalFunctionStat":
                fn = stat["FunctionStat"]
                origfn = fn["NameChain"][0]["Source"]
                newfn = allocname()
                scopes[-1][origfn] = newfn
                fn["NameChain"][0]["Source"] = newfn
                scopes.append({})
                for p in fn.get("ArgList", []):
                    if p["Source"] != "...":
                        newp = allocname()
                        scopes[-1][p["Source"]] = newp
                        p["Source"] = newp
                for s in fn["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
            elif typ == "FunctionStat":
                if len(stat.get("NameChain", [])) == 1:
                    origfn = stat["NameChain"][0]["Source"]
                    mapped = lookup(origfn)
                    if mapped is not None:
                        stat["NameChain"][0]["Source"] = mapped
                scopes.append({})
                for p in stat.get("ArgList", []):
                    if p["Source"] != "...":
                        newp = allocname()
                        scopes[-1][p["Source"]] = newp
                        p["Source"] = newp
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
            elif typ == "AssignmentStat":
                for r in stat.get("Rhs", []):
                    visitexpr(r)
                for l in stat.get("Lhs", []):
                    visitexpr(l)
            elif typ == "CallExprStat":
                visitexpr(stat["Expression"])
            elif typ == "ReturnStat":
                for e in stat.get("ExprList", []):
                    visitexpr(e)
            elif typ == "IfStat":
                visitexpr(stat["Condition"])
                scopes.append({})
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
                for clause in stat.get("ElseClauseList", []):
                    if clause.get("Condition") is not None:
                        visitexpr(clause["Condition"])
                    scopes.append({})
                    for s in clause["Body"]["StatementList"]:
                        visitstat(s)
                    scopes.pop()
            elif typ == "WhileStat":
                visitexpr(stat["Condition"])
                scopes.append({})
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
            elif typ == "RepeatStat":
                scopes.append({})
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                visitexpr(stat["Condition"])
                scopes.pop()
            elif typ == "DoStat":
                scopes.append({})
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
            elif typ == "NumericForStat":
                for r in stat.get("RangeList", []):
                    if r is not None:
                        visitexpr(r)
                scopes.append({})
                for v in stat.get("VarList", []):
                    orig = v["Source"]
                    newv = allocname()
                    scopes[-1][orig] = newv
                    v["Source"] = newv
                    v["Name"] = newv
                    if "Variable" in stat:
                        stat["Variable"]["Variable"]["Name"] = newv
                        stat["Variable"]["Token"]["Source"] = newv
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()
            elif typ == "GenericForStat":
                for g in stat.get("ExprList", []):
                    visitexpr(g)
                scopes.append({})
                for i, v in enumerate(stat.get("VarList", [])):
                    orig = v["Source"]
                    newv = allocname()
                    scopes[-1][orig] = newv
                    v["Source"] = newv
                    v["Name"] = newv
                    if "Names" in stat and i < len(stat["Names"]):
                        stat["Names"][i]["Variable"]["Name"] = newv
                        stat["Names"][i]["Token"]["Source"] = newv
                for s in stat["Body"]["StatementList"]:
                    visitstat(s)
                scopes.pop()

        for s in ast.get("StatementList", []):
            visitstat(s)
    return ast


def refineastnode(ast, options=None):
    return refineast(ast, options)


def serializenode(node):
    if isinstance(node, dict):
        typ = node.get("Type")
        if typ in ("Chunk", "StatList"):
            return "\n".join(serializenode(s) for s in node.get("StatementList", []))
        elif typ == "AssignmentStat":
            lhs = ", ".join(serializenode(v) for v in node.get("Lhs", []))
            rhs = ", ".join(serializenode(v) for v in node.get("Rhs", []))
            return f"{lhs} = {rhs}"
        elif typ == "LocalVarStat":
            varsstr = ", ".join(v["Source"] for v in node.get("VarList", []))
            exprs = ", ".join(serializenode(v) for v in node.get("ExprList", []))
            if exprs:
                return f"local {varsstr} = {exprs}"
            return f"local {varsstr}" if varsstr else "local"
        elif typ == "LocalFunctionStat":
            fn = node["FunctionStat"]
            name = fn["NameChain"][0]["Source"]
            params = ", ".join(p["Source"] for p in fn.get("ArgList", []))
            body = serializenode(fn["Body"])
            return f"local function {name}({params})\n{body}\nend"
        elif typ in ("FunctionStat", "FunctionDef"):
            if "NameChain" in node:
                name = ".".join(p["Source"] for p in node["NameChain"])
            else:
                name = serializenode(node["Name"]) if node.get("Name") else ""
            params = ", ".join(p["Source"] if "Source" in p else serializenode(p) for p in node.get("ArgList", node.get("Parameters", [])))
            body = serializenode(node["Body"])
            return f"function {name}({params})\n{body}\nend"
        elif typ == "FunctionLiteral":
            params = ", ".join(p["Source"] for p in node.get("ArgList", []))
            body = serializenode(node["Body"])
            return f"function({params})\n{body}\nend"
        elif typ == "VariableExpr":
            return node["Variable"]["Name"]
        elif typ == "NumberLiteral":
            return node["Token"]["Source"]
        elif typ == "StringLiteral":
            return f'"{node["Token"]["Source"]}"'
        elif typ == "NilLiteral":
            return "nil"
        elif typ == "DotsExpr":
            return "..."
        elif typ == "BooleanLiteral":
            return node["Token"]["Source"]
        elif typ == "BinopExpr":
            lhs = serializenode(node["Lhs"])
            rhs = serializenode(node["Rhs"])
            op = node["Token_Op"]["Source"]
            return f"({lhs} {op} {rhs})"
        elif typ == "UnopExpr":
            rhs = serializenode(node["Rhs"])
            op = node["Token_Op"]["Source"]
            return f"{op}({rhs})"
        elif typ == "CallExprStat":
            return serializenode(node["Expression"])
        elif typ == "CallExpr":
            base = serializenode(node["Base"])
            args = ", ".join(serializenode(a) for a in node["FunctionArguments"]["ArgList"])
            return f"{base}({args})"
        elif typ == "IndexExpr":
            base = serializenode(node["Base"])
            idx = serializenode(node["Index"])
            return f"{base}[{idx}]"
        elif typ == "FieldExpr":
            base = serializenode(node["Base"])
            field = node["Field"]["Source"]
            return f"{base}.{field}"
        elif typ == "MethodExpr":
            base = serializenode(node["Base"])
            method = node["Method"]["Source"]
            return f"{base}:{method}"
        elif typ == "ParenExpr":
            return f"({serializenode(node['Expression'])})"
        elif typ == "ReturnStat":
            exprs = ", ".join(serializenode(v) for v in node.get("ExprList", []))
            return f"return {exprs}" if exprs else "return"
        elif typ == "BreakStat":
            return "break"
        elif typ == "DoStat":
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            return f"do\n{body}\nend"
        elif typ == "IfStat":
            cond = serializenode(node["Condition"])
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            elseparts = []
            for elseclause in node.get("ElseClauseList", []):
                if elseclause.get("ClauseType") == "elseif":
                    econd = serializenode(elseclause["Condition"])
                    ebody = "\n".join(serializenode(s) for s in elseclause["Body"]["StatementList"])
                    elseparts.append(f"elseif {econd} then\n{ebody}")
                else:
                    ebody = "\n".join(serializenode(s) for s in elseclause["Body"]["StatementList"])
                    elseparts.append(f"else\n{ebody}")
            tail = ("\n" + "\n".join(elseparts)) if elseparts else ""
            return f"if {cond} then\n{body}{tail}\nend"
        elif typ == "WhileStat":
            cond = serializenode(node["Condition"])
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            return f"while {cond} do\n{body}\nend"
        elif typ == "RepeatStat":
            cond = serializenode(node["Condition"])
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            return f"repeat\n{body}\nuntil {cond}"
        elif typ == "NumericForStat":
            var = node["VarList"][0]["Source"] if "VarList" in node else serializenode(node.get("Variable", {}))
            start = serializenode(node["RangeList"][0])
            end = serializenode(node["RangeList"][1])
            step = serializenode(node["RangeList"][2]) if len(node["RangeList"]) > 2 and node["RangeList"][2] is not None else ""
            stepstr = f", {step}" if step else ""
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            return f"for {var} = {start}, {end}{stepstr} do\n{body}\nend"
        elif typ == "GenericForStat":
            names = ", ".join(v["Source"] for v in node["VarList"]) if "VarList" in node else ", ".join(serializenode(v) for v in node.get("Names", []))
            exprs = ", ".join(serializenode(v) for v in node.get("ExprList", []))
            body = "\n".join(serializenode(s) for s in node["Body"]["StatementList"])
            return f"for {names} in {exprs} do\n{body}\nend"
        elif typ == "TableLiteral":
            fields = []
            for f in node.get("EntryList", node.get("Fields", [])):
                etype = f.get("EntryType")
                if etype == "Field":
                    fields.append(f"{f['Field']['Source']} = {serializenode(f['Value'])}")
                elif etype == "Index" or f.get("Key") is not None:
                    key = serializenode(f["Key"])
                    val = serializenode(f["Value"])
                    fields.append(f"[{key}] = {val}")
                else:
                    val = serializenode(f["Value"])
                    fields.append(val)
            return "{" + ", ".join(fields) + "}"
        else:
            return str(node)
    elif isinstance(node, list):
        return "\n".join(serializenode(v) for v in node)
    else:
        return str(node)


def displayast(ast):
    if ast is None:
        return ""
    return serializenode(ast)


def numval(node):
    if isinstance(node, dict):
        if node.get("Type") == "ParenExpr":
            return numval(node.get("Expression"))
        if node.get("Type") == "NumberLiteral":
            src = node["Token"]["Source"]
            try:
                return int(src, 0)
            except ValueError:
                try:
                    return float(src)
                except ValueError:
                    return None
    return None


def fmtnum(val):
    if isinstance(val, float) and int(val) == val:
        val = int(val)
    s = str(val)
    return {
        "Type": "NumberLiteral",
        "Source": s,
        "Token": maketoken("Number", s),
    }


def resolvearithmetic(ast):
    def fold(node):
        if isinstance(node, dict):
            typ = node.get("Type")
            if typ == "BinopExpr":
                node["Lhs"] = fold(node["Lhs"])
                node["Rhs"] = fold(node["Rhs"])
                lv = numval(node["Lhs"])
                rv = numval(node["Rhs"])
                if lv is not None and rv is not None:
                    op = node["Token_Op"]["Source"]
                    try:
                        if op == "+": res = lv + rv
                        elif op == "-": res = lv - rv
                        elif op == "*": res = lv * rv
                        elif op == "/": res = lv / rv
                        elif op == "^": res = lv ** rv
                        elif op == "%": res = lv % rv
                        else: return node
                        return fmtnum(res)
                    except Exception:
                        return node
                return node
            elif typ == "UnopExpr":
                node["Rhs"] = fold(node["Rhs"])
                op = node["Token_Op"]["Source"]
                inner = node["Rhs"]
                if inner.get("Type") == "ParenExpr":
                    inner = inner["Expression"]
                if op == "-":
                    rv = numval(inner)
                    if rv is not None:
                        return fmtnum(-rv)
                elif op == "#":
                    if inner.get("Type") == "StringLiteral":
                        return fmtnum(len(inner["Token"]["Source"]))
                    elif inner.get("Type") == "TableLiteral":
                        return fmtnum(len(inner.get("EntryList", inner.get("Fields", []))))
                return node
            elif typ == "ParenExpr":
                node["Expression"] = fold(node["Expression"])
                if node["Expression"].get("Type") == "NumberLiteral":
                    return node["Expression"]
                return node
            else:
                for key, value in list(node.items()):
                    if isinstance(value, (dict, list)):
                        node[key] = fold(value)
                return node
        elif isinstance(node, list):
            return [fold(item) for item in node]
        return node

    return fold(ast)
