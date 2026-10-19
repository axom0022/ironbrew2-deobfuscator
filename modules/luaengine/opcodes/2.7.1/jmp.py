jmp = {
    "Thorough": True,
    "String": "InstrPoint=Inst[OP_B];",
    "Create": lambda inst: inst.update({"B": inst["B"] - inst["PC"] - 1}) or inst
}
