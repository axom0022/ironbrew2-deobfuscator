eq = {
    "String": "if(Stk[Inst[OP_A]]==Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 0}) or inst
}

eqb = {
    "String": "if(Inst[OP_A] == Stk[Inst[OP_C]]) then InstrPoint = InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 0}) or inst
}

eqc = {
    "String": "if(Stk[Inst[OP_A]] == Inst[OP_C])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 0}) or inst
}

eqbc = {
    "String": "if(Inst[OP_A] == Inst[OP_C]) then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 0}) or inst
}

ne = {
    "String": "if(Stk[Inst[OP_A]]~=Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 1}) or inst
}

neb = {
    "String": "if(Inst[OP_A] ~= Stk[Inst[OP_C]]) then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 1}) or inst
}

nec = {
    "String": "if(Stk[Inst[OP_A]] ~= Inst[OP_C]) then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 1}) or inst
}

nebc = {
    "String": "if(Inst[OP_A] ~= Inst[OP_C])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 1}) or inst
}
