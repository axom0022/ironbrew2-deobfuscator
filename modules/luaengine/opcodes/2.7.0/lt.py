lt = {
    "Thorough": True,
    "String": "if(Stk[Inst[OP_A]] < Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 0}) or inst
}

ltb = {
    "Thorough": True,
    "String": "if(Const[Inst[OP_A]] < Stk[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 0}) or inst
}

ltc = {
    "Thorough": True,
    "String": "if(Stk[Inst[OP_A]] < Const[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 0}) or inst
}

ltbc = {
    "Thorough": True,
    "String": "if(Const[Inst[OP_A]] < Const[Inst[OP_C]])then InstrPoint=InstrPoint+1;else InstrPoint=Inst[OP_B];end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 0}) or inst
}

ge = {
    "Thorough": True,
    "String": "if (Stk[Inst[OP_A]]<Stk[Inst[OP_C]])then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "A": 1}) or inst
}

geb = {
    "Thorough": True,
    "String": "if (Const[Inst[OP_A]] < Stk[Inst[OP_C]]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "A": 1}) or inst
}

gec = {
    "Thorough": True,
    "String": "if (Stk[Inst[OP_A]] < Const[Inst[OP_C]]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"], "C": inst["C"] + 255, "A": 1}) or inst
}

gebc = {
    "Thorough": True,
    "String": "if (Const[Inst[OP_A]] < Const[Inst[OP_C]]) then InstrPoint=Inst[OP_B]; else InstrPoint=InstrPoint+1; end;",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": inst["A"] + 255, "C": inst["C"] + 255, "A": 1}) or inst
}
