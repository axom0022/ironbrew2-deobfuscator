tailcall = {
    "String": "local A = Inst[OP_A]; do return Stk[A](Unpack(Stk, A + 1, Inst[OP_B])) end;",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": 0}) or inst
}

tailcallb0 = {
    "String": "local A = Inst[OP_A]; do return Stk[A](Unpack(Stk, A + 1, Top)) end;",
    "Create": lambda inst: inst.update({"B": 0, "C": 0}) or inst
}

tailcallb1 = {
    "String": "do return Stk[Inst[OP_A]](); end;",
    "Create": lambda inst: inst.update({"B": 1, "C": 0}) or inst
}
