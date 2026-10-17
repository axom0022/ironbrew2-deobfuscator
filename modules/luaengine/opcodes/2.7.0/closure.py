def matchclosure(instruction):
    if len(instruction) > 3 and instruction[3].get("Type") == "AssignmentStat":
        s = instruction[3]
        if s["Rhs"] and s["Rhs"][0].get("Type") == "CallExpr":
            r = s["Rhs"][0]
            args = r["FunctionArguments"].get("ArgList", [])
            if len(args) > 1 and args[1].get("Type") == "TableLiteral":
                entries = args[1].get("EntryList", args[1].get("Fields", []))
                if len(entries) > 1:
                    first = entries[0]
                    if "Field" in first and first["Field"]["Source"] == "__index":
                        return True
    return False

closure = {
    "Match": matchclosure,
    "Create": lambda inst: inst.update({"UpvalueCount": inst.get("C") or 0}) or inst
}

closurenu = {
    "String": "Stk[Inst[OP_A]]=Wrap(Proto[Inst[OP_B]],nil,Env);",
    "Create": lambda inst: inst.update({"UpvalueCount": 0, "C": 0}) or inst
}
