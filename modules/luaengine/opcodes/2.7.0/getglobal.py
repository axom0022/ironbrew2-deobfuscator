getglobal = {
    "Thorough": True,
    "String": "Stk[Inst[OP_A]]=Env[Const[Inst[OP_B]]];",
    "Create": lambda inst: inst.update({"B": inst["B"] - 1}) or inst
}
