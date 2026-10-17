test = {
    "String": "if Stk[Inst[OP_A]] then InstrPoint=InstrPoint + 1; else InstrPoint=InstrPoint+Inst[OP_B]; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": 0, "C": 0}) or inst
}

testc = {
    "String": "if not Stk[Inst[OP_A]] then InstrPoint=InstrPoint+1;else InstrPoint=InstrPoint+Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": 0, "C": 1}) or inst
}
