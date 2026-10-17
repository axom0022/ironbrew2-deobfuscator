ret = {
    "String": "local A = Inst[OP_A];\ndo return Unpack(Stk, A, A + Inst[OP_B]) end;",
    "Create": lambda inst: inst.update({"B": inst["B"] + 2, "C": 0}) or inst
}

returnb2 = {
    "String": "do return Stk[Inst[OP_A]] end",
    "Create": lambda inst: inst.update({"B": 2, "C": 0}) or inst
}

returnb3 = {
    "String": "local A = Inst[OP_A];\ndo return Stk[A], Stk[A + 1] end",
    "Create": lambda inst: inst.update({"B": 3, "C": 0}) or inst
}

returnb0 = {
    "String": "local A = Inst[OP_A];\ndo return Unpack(Stk, A, Top) end;",
    "Create": lambda inst: inst.update({"B": 0, "C": 0}) or inst
}

returnb1 = {
    "String": "do return end;",
    "Create": lambda inst: inst.update({"B": 1, "C": 0}) or inst
}
