def tonum(val):
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    try:
        return int(s, 0)
    except ValueError:
        return float(s)


def computeunary(node):
    if not isinstance(node, dict) or node.get("Type") != "UnopExpr":
        return None
    op = node["Token_Op"]["Source"]
    rhs = node["Rhs"]
    while isinstance(rhs, dict) and rhs.get("Type") == "ParenExpr":
        rhs = rhs["Expression"]
    if op == "#":
        if rhs.get("Type") == "StringLiteral":
            return len(rhs["Token"]["Source"])
        elif rhs.get("Type") == "TableLiteral":
            return len(rhs.get("EntryList", rhs.get("Fields", [])))
        return None
    elif op == "-":
        if rhs.get("Type") == "NumberLiteral":
            v = tonum(rhs["Token"]["Source"])
            return -v
        return None
    return None


def computebinary(lhs, op, rhs):
    l = tonum(lhs)
    r = tonum(rhs)
    if op == "==": return l == r
    elif op == "~=": return l != r
    elif op == "<=": return l <= r
    elif op == ">=": return l >= r
    elif op == "<": return l < r
    elif op == ">": return l > r
    elif op == "-": return l - r
    elif op == "+": return l + r
    elif op == "/": return l / r
    elif op == "^": return l ** r
    elif op == "*": return l * r
    elif op == "%": return l % r
    raise ValueError(f"Unsupported operator: {op}")


def bxor(a, b):
    return (int(a) & 0xFFFFFFFF) ^ (int(b) & 0xFFFFFFFF)


def gbit(bit, start, end=None):
    bit = int(bit)
    if end is not None:
        mask = (1 << (end - start + 1)) - 1
        return (bit >> (start - 1)) & mask
    return (bit >> (start - 1)) & 1


def decompress(bytestring, key):
    words = [bytes([i]) for i in range(256)]
    out = bytearray()
    pos = 0
    n = len(bytestring)
    current = None

    while pos < n:
        length = int(bytestring[pos], 36)
        pos += 1
        entry = int(bytestring[pos:pos + length], 36)
        pos += length

        if current is None:
            current = bytes([entry & 0xFF])
            out.extend(current)
            continue

        if entry < len(words):
            word = words[entry]
        else:
            word = current + current[:1]

        words.append(current + word[:1])
        out.extend(word)
        current = word

    if key:
        k = int(key) & 0xFF
        return bytes(b ^ k for b in out)
    return bytes(out)


def decode(bytestring, key):
    parts = [p for p in bytestring.split("\\") if p]
    k = int(key) & 0xFF
    return bytes((int(p) ^ k) & 0xFF for p in parts)
