vararg = {
    "String": "local A=Inst[OP_A];local B=Inst[OP_B];for Idx=A,B do Stk[Idx]=Vararg[Idx-A];end;",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": 0}) or inst
}

varargb0 = {
    "String": "local A=Inst[OP_A];Top=A+Varargsz-1;for Idx=A,Top do local VA=Vararg[Idx-A];Stk[Idx]=VA;end;",
    "Create": lambda inst: inst.update({"B": 0, "C": 0}) or inst
}
