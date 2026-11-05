tforloop = {
    "String": """local A = Inst[OP_A];
local C = Inst[OP_C];
local CB = A + 2
local Result = {Stk[A](Stk[A + 1],Stk[CB])};
for Idx = 1, C do 
Stk[CB + Idx] = Result[Idx];
end;
local R = Result[1]
if R then 
Stk[CB] = R 
InstrPoint = Inst[OP_B];
else
InstrPoint = InstrPoint + 1;
end;""",
    "Create": lambda inst: inst.update({"_ib2_target": inst["B"], "B": 0}) or inst
}
