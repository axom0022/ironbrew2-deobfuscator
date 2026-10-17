call = {
    "String": """local A = Inst[OP_A]
local Results = { Stk[A](Unpack(Stk, A + 1, Inst[OP_B])) };
local Edx = 0;
for Idx = A, Inst[OP_C] do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end""",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": inst["C"] - inst["A"] + 2}) or inst
}

callb2 = {
    "String": """local A = Inst[OP_A]
local Results = { Stk[A](Stk[A + 1]) };
local Edx = 0;
for Idx = A, Inst[OP_C] do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end""",
    "Create": lambda inst: inst.update({"B": 2, "C": inst["C"] - inst["A"] + 2}) or inst
}

callb0 = {
    "String": """local A = Inst[OP_A]
local Results = { Stk[A](Unpack(Stk, A + 1, Top)) };
local Edx = 0;
for Idx = A, Inst[OP_C] do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end""",
    "Create": lambda inst: inst.update({"B": 0, "C": inst["C"] - inst["A"] + 2}) or inst
}

callb1 = {
    "String": """local A = Inst[OP_A]
local Results = { Stk[A]() };
local Limit = Inst[OP_C];
local Edx = 0;
for Idx = A, Limit do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end""",
    "Create": lambda inst: inst.update({"B": 1, "C": inst["C"] - inst["A"] + 2}) or inst
}

callc0 = {
    "String": """local A = Inst[OP_A]
local Results, Limit = _R(Stk[A](Unpack(Stk, A + 1, Inst[OP_B])))
Top = Limit + A - 1
local Edx = 0;
for Idx = A, Top do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end;""",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": 0}) or inst
}

callc0b2 = {
    "String": """local A = Inst[OP_A]
local Results, Limit = _R(Stk[A](Stk[A + 1]))
Top = Limit + A - 1
local Edx = 0;
for Idx = A, Top do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end;""",
    "Create": lambda inst: inst.update({"B": 2, "C": 0}) or inst
}

callc1 = {
    "String": "local A = Inst[OP_A]\nStk[A](Unpack(Stk, A + 1, Inst[OP_B]))",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": 1}) or inst
}

callc1b2 = {
    "String": "local A = Inst[OP_A]\nStk[A](Stk[A + 1])",
    "Create": lambda inst: inst.update({"B": 2, "C": 1}) or inst
}

callb0c0 = {
    "String": """local A = Inst[OP_A]
local Results, Limit = _R(Stk[A](Unpack(Stk, A + 1, Top)))
Top = Limit + A - 1
local Edx = 0;
for Idx = A, Top do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end;""",
    "Create": lambda inst: inst.update({"B": 0, "C": 0}) or inst
}

callb0c1 = {
    "String": "local A = Inst[OP_A]\nStk[A](Unpack(Stk, A + 1, Top))",
    "Create": lambda inst: inst.update({"B": 0, "C": 1}) or inst
}

callb1c0 = {
    "String": """local A = Inst[OP_A]
local Results, Limit = _R(Stk[A]())
Top = Limit + A - 1
local Edx = 0;
for Idx = A, Top do 
Edx = Edx + 1;
Stk[Idx] = Results[Edx];
end;""",
    "Create": lambda inst: inst.update({"B": 1, "C": 0}) or inst
}

callb1c1 = {
    "String": "Stk[Inst[OP_A]]();",
    "Create": lambda inst: inst.update({"B": 1, "C": 1}) or inst
}

callc2 = {
    "String": "local A = Inst[OP_A]\nStk[A] = Stk[A](Unpack(Stk, A + 1, Inst[OP_B]))",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["A"] + 1, "C": 2}) or inst
}

callc2b2 = {
    "String": "local A = Inst[OP_A]\nStk[A] = Stk[A](Stk[A + 1]) ",
    "Create": lambda inst: inst.update({"B": 2, "C": 2}) or inst
}

callb0c2 = {
    "String": "local A = Inst[OP_A]\nStk[A] = Stk[A](Unpack(Stk, A + 1, Top))",
    "Create": lambda inst: inst.update({"B": 0, "C": 2}) or inst
}

callb1c2 = {
    "String": "local A = Inst[OP_A]\nStk[A] = Stk[A]()",
    "Create": lambda inst: inst.update({"B": 1, "C": 2}) or inst
}
