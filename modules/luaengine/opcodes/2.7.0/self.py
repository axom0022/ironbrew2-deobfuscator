self = {
    "String": "local A=Inst[OP_A];local B=Stk[Inst[OP_B]];Stk[A+1]=B;Stk[A]=B[Stk[Inst[OP_C]]];",
    "Create": lambda inst: inst
}

selfc = {
    "String": "local A=Inst[OP_A];local B=Stk[Inst[OP_B]];Stk[A+1]=B;Stk[A]=B[Const[Inst[OP_C]]];",
    "Create": lambda inst: inst.update({"C": inst["C"] + 255}) or inst
}
