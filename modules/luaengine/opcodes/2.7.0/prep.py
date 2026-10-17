forprep = {
    "String": """local A = Inst[OP_A];
local Index = Stk[A]
local Step = Stk[A + 2];
if (Step > 0) then 
if (Index > Stk[A+1]) then
InstrPoint = Inst[OP_B];
else
Stk[A+3] = Index;
end
elseif (Index < Stk[A+1]) then
InstrPoint = Inst[OP_B];
else
Stk[A+3] = Index;
end""",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["PC"] - 2}) or inst
}
