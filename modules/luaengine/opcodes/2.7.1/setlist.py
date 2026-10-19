setlist = {
    "String": "local A = Inst[OP_A]; local T = Stk[A]; for Idx = A + 1, Inst[OP_B] do Insert(T, Stk[Idx]) end;",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"], "C": inst.get("C") or 1}) or inst
}

setlistb0 = {
    "String": "local A = Inst[OP_A]; local T = Stk[A]; for Idx = A + 1, Top do Insert(T, Stk[Idx]) end;",
    "Create": lambda inst: inst.update({"B": 0, "C": inst.get("C") or 1}) or inst
}

setlistc0 = {
    "String": "InstrPoint = InstrPoint + 1 local A = Inst[OP_A]; local T = Stk[A]; for Idx = A + 1, Inst[OP_B] do Insert(T, Stk[Idx]) end;",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"], "C": 1}) or inst
}
