mul = {
    "String": "Stk[Inst[OP_A]]=Stk[Inst[OP_B]]*Stk[Inst[OP_C]]",
    "Create": lambda inst: inst
}

mulb = {
    "String": "Stk[Inst[OP_A]] = Const[Inst[OP_B]] * Stk[Inst[OP_C]]",
    "Create": lambda inst: inst.update({"B": inst["B"] + 255}) or inst
}

mulc = {
    "String": "Stk[Inst[OP_A]] = Stk[Inst[OP_B]] * Const[Inst[OP_C]]",
    "Create": lambda inst: inst.update({"C": inst["C"] + 255}) or inst
}

mulbc = {
    "String": "Stk[Inst[OP_A]] = Const[Inst[OP_B]] * Const[Inst[OP_C]]",
    "Create": lambda inst: inst.update({"B": inst["B"] + 255, "C": inst["C"] + 255}) or inst
}
