loadbool = {
    "String": "Stk[Inst[OP_A]]=(Inst[OP_B]~=0);",
    "Create": lambda inst: inst.update({"C": 0}) or inst
}

loadboolc = {
    "String": "Stk[Inst[OP_A]]=(Inst[OP_B]~=0);InstrPoint=InstrPoint+1;",
    "Create": lambda inst: inst.update({"C": 1}) or inst
}
