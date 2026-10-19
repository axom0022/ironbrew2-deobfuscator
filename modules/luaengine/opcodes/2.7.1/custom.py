settop = {
    "Thorough": True,
    "String": "Top = Inst[OP_A];",
    "Create": lambda inst: inst.update({"CustomOp": "settop", "OrigA": inst["A"], "A": 0, "B": 0, "C": 0}) or inst
}

newstack = {
    "String": "Stk = {};for Idx = 0, PCount do if Idx < Params then Stk[Idx] = Args[Idx + 1]; else break end; end;",
    "Create": lambda inst: inst.update({"CustomOp": "newstack", "A": 0, "B": 0, "C": 0}) or inst
}

setfenv = {
    "Thorough": True,
    "String": "Env = Stk[Inst[OP_A]]",
    "Create": lambda inst: inst.update({"CustomOp": "setfenv", "OrigA": inst["A"], "A": 0, "B": 0, "C": 0}) or inst
}

pushstack = {
    "Thorough": True,
    "String": "Stk[Inst[OP_A]] = Stk",
    "Create": lambda inst: inst.update({"CustomOp": "pushstack", "OrigA": inst["A"], "A": 0, "B": 0, "C": 0}) or inst
}
