le = {
    "Thorough": True,
    "String": "if(Stk[Inst[OP_A]]<=Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 0}) or inst
}

leb = {
    "Thorough": True,
    "String": "if(Inst[OP_A] <= Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 0}) or inst
}

lec = {
    "Thorough": True,
    "String": "if(Stk[Inst[OP_A]] <= Inst[OP_C])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 0}) or inst
}

lebc = {
    "Thorough": True,
    "String": "if(Inst[OP_A] <= Inst[OP_C])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 0}) or inst
}

gt = {
    "Thorough": True,
    "String": "if (Stk[Inst[OP_A]] <= Stk[Inst[OP_C]]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 1}) or inst
}

gtb = {
    "Thorough": True,
    "String": "if (Inst[OP_A] <= Stk[Inst[OP_C]]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 1}) or inst
}

gtc = {
    "Thorough": True,
    "String": "if (Stk[Inst[OP_A]] <= Inst[OP_C]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 1}) or inst
}

gtbc = {
    "Thorough": True,
    "String": "if (Inst[OP_A] <= Inst[OP_C]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 1}) or inst
}
