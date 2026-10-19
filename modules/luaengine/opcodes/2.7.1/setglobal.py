setglobal = {
    "Thorough": True,
    "String": "Env[Inst[OP_B]] = Stk[Inst[OP_A]];",
    "Create": lambda inst: inst.update({"B": inst["B"] - 1}) or inst
}
