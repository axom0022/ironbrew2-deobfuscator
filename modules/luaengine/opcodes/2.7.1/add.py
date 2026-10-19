add = {
    "String": "Stk[Inst[OP_A]]=Stk[Inst[OP_B]]+Stk[Inst[OP_C]]",
    "Create": lambda inst: inst
}

addb = {
    "String": "Stk[Inst[OP_A]] = Inst[OP_B] + Stk[Inst[OP_C]]",
    "Create": lambda inst: inst.update({"B": inst["B"] + 255}) or inst
}

addc = {
    "String": "Stk[Inst[OP_A]] = Stk[Inst[OP_B]] + Inst[OP_C]",
    "Create": lambda inst: inst.update({"C": inst["C"] + 255}) or inst
}

addbc = {
    "String": "Stk[Inst[OP_A]] = Inst[OP_B] + Inst[OP_C]",
    "Create": lambda inst: inst.update({"B": inst["B"] + 255, "C": inst["C"] + 255}) or inst
}
