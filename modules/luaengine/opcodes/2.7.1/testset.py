testset = {
    "String": "local B=Stk[Inst[OP_C]];if B then InstrPoint=InstrPoint+1;else Stk[Inst[OP_A]]=B;InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["C"], "C": 0}) or inst
}

testsetc = {
    "String": "local B=Stk[Inst[OP_C]];if not B then InstrPoint=InstrPoint+1;else Stk[Inst[OP_A]]=B;InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["C"], "C": 1}) or inst
}
