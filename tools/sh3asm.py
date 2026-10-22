#!/usr/bin/env python3
"""Tiny SH-3 assembler for the few instructions used by the Show Time patch routines.
Usage: assemble(base, src) -> bytes.  Labels end with ':'; '.long X' and '.word X' emit data
(X may be a label or number); '.align 4' pads with 0x0009.  mov.l/mov.w @label,Rn use PC-relative."""
import re

def _r(s):
    m = re.fullmatch(r"r(\d+)", s.strip())
    if not m: raise ValueError(f"bad register {s}")
    return int(m.group(1))

def _imm(s, labels=None):
    s = s.strip().lstrip("#")
    if labels is not None and s in labels: return labels[s]
    return int(s, 0)

def assemble(base, src):
    lines = []
    for raw in src.split("\n"):
        line = raw.split(";")[0].strip()
        if not line: continue
        while True:
            m = re.match(r"^(\w+):\s*(.*)$", line)
            if not m: break
            lines.append(("label", m.group(1))); line = m.group(2).strip()
        if line: lines.append(("ins", line))

    def size(ins, addr):
        op = ins.split()[0]
        if op == ".long": return 4
        if op == ".word": return 2
        if op == ".align": return (-addr) % int(ins.split()[1])
        return 2

    labels, addr = {}, base
    for kind, v in lines:
        if kind == "label": labels[v] = addr
        else: addr += size(v, addr)

    out, addr = bytearray(), base
    for kind, v in lines:
        if kind == "label": continue
        op, _, args = v.partition(" ")
        a = [x.strip() for x in re.split(r",(?![^(]*\))", args)] if args.strip() else []
        def emit(w): out.extend(int(w).to_bytes(2, "big"))
        if op == ".long": out.extend((_imm(a[0], labels) & 0xFFFFFFFF).to_bytes(4, "big"))
        elif op == ".word": out.extend((_imm(a[0], labels) & 0xFFFF).to_bytes(2, "big"))
        elif op == ".align":
            n = (-addr) % int(a[0]); assert n % 2 == 0
            for _ in range(n // 2): emit(0x0009)
        elif op in ("mov.l", "mov.w") and a[0].startswith("@") and a[0][1:] in labels:
            tgt = labels[a[0][1:]]; n = _r(a[1])
            if op == "mov.l":
                d = (tgt - ((addr & ~3) + 4)); assert d % 4 == 0 and 0 <= d // 4 <= 255, v
                emit(0xD000 | n << 8 | d // 4)
            else:
                d = tgt - (addr + 4); assert d % 2 == 0 and 0 <= d // 2 <= 255, v
                emit(0x9000 | n << 8 | d // 2)
        elif op == "mov.b" and re.fullmatch(r"@\(\d+,r\d+\)", a[0]):     # mov.b @(d,Rm),r0
            d, m = re.fullmatch(r"@\((\d+),(r\d+)\)", a[0]).groups(); assert a[1] == "r0"
            emit(0x8400 | _r(m) << 4 | int(d))
        elif op == "mov.b" and re.fullmatch(r"@\(\d+,r\d+\)", a[1]):     # mov.b r0,@(d,Rn)
            d, n = re.fullmatch(r"@\((\d+),(r\d+)\)", a[1]).groups(); assert a[0] == "r0"
            emit(0x8000 | _r(n) << 4 | int(d))
        elif op in ("mov.b", "mov.l") and a[0].startswith("@"):         # mov.x @Rm,Rn
            emit(0x6000 | _r(a[1]) << 8 | _r(a[0][1:]) << 4 | {"mov.b": 0, "mov.l": 2}[op])
        elif op in ("mov.b", "mov.l") and a[1].startswith("@"):         # mov.x Rm,@Rn
            emit(0x2000 | _r(a[1][1:]) << 8 | _r(a[0]) << 4 | {"mov.b": 0, "mov.l": 2}[op])
        elif op == "mov" and a[0].startswith("#"): emit(0xE000 | _r(a[1]) << 8 | (_imm(a[0]) & 0xFF))
        elif op == "mov": emit(0x6003 | _r(a[1]) << 8 | _r(a[0]) << 4)
        elif op == "extu.b": emit(0x600C | _r(a[1]) << 8 | _r(a[0]) << 4)
        elif op == "add" and a[0].startswith("#"): emit(0x7000 | _r(a[1]) << 8 | (_imm(a[0]) & 0xFF))
        elif op == "add": emit(0x300C | _r(a[1]) << 8 | _r(a[0]) << 4)
        elif op in ("and", "or", "xor", "tst") and a[0].startswith("#"):
            assert a[1] == "r0"; emit({"and": 0xC900, "or": 0xCB00, "xor": 0xCA00, "tst": 0xC800}[op] | (_imm(a[0]) & 0xFF))
        elif op in ("and", "or", "xor", "tst"):
            emit(0x2000 | _r(a[1]) << 8 | _r(a[0]) << 4 | {"and": 9, "or": 0xB, "xor": 0xA, "tst": 8}[op])
        elif op == "cmp/eq" and a[0].startswith("#"): assert a[1] == "r0"; emit(0x8800 | (_imm(a[0]) & 0xFF))
        elif op in ("cmp/eq", "cmp/hs", "cmp/hi", "cmp/ge", "cmp/gt"):
            emit(0x3000 | _r(a[1]) << 8 | _r(a[0]) << 4 | {"cmp/eq": 0, "cmp/hs": 2, "cmp/ge": 3, "cmp/hi": 6, "cmp/gt": 7}[op])
        elif op == "movt": emit(0x0029 | _r(a[0]) << 8)
        elif op == "dt": emit(0x4010 | _r(a[0]) << 8)
        elif op in ("bt", "bf"):
            d = labels[a[0]] - (addr + 4); assert d % 2 == 0 and -256 <= d // 2 <= 127, v
            emit((0x8900 if op == "bt" else 0x8B00) | (d // 2) & 0xFF)
        elif op in ("bra", "bsr"):
            d = labels[a[0]] - (addr + 4); assert d % 2 == 0 and -2048 <= d // 2 <= 2047, v
            emit((0xA000 if op == "bra" else 0xB000) | (d // 2) & 0xFFF)
        elif op == "jmp": emit(0x402B | _r(a[0][1:]) << 8)
        elif op == "jsr": emit(0x400B | _r(a[0][1:]) << 8)
        elif op == "rts": emit(0x000B)
        elif op == "nop": emit(0x0009)
        elif op == "sts.l" and a == ["pr", "@-r15"]: emit(0x4F22)
        elif op == "lds.l" and a == ["@r15+", "pr"]: emit(0x4F26)
        else: raise ValueError(f"unknown instruction: {v}")
        addr = base + len(out)
    return bytes(out)
