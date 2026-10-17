gettable = {
    "String": "Stk[Inst[OP_A]]=Stk[Inst[OP_B]][Stk[Inst[OP_C]]];",
    "Create": lambda inst: inst
}

gettableconst = {
    "String": "Stk[Inst[OP_A]]=Stk[Inst[OP_B]][Const[Inst[OP_C]]];",
    "Create": lambda inst: inst.update({"C": inst["C"] + 255}) or inst
}
