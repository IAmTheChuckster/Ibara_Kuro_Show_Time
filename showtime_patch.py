#!/usr/bin/env python3
"""Build the Ibara Kuro "Show Time" ROMs from your own Ibara Kuro Black Label dump.

    ibarablk_u4  ->  ibarashow_u4   (program)
    u23          ->  ibarashow_u23  (sound-chip sequence table)

What the Show Time build changes:
  * music: Bonds of Steel -> Show Time, Air Pollution -> Sky High,
    The Family's Work -> Robot No28 (play times and titles follow)
  * warning screen: new disclaimer text; boot line "2026/10/22 SHOW TIME"
  * title screen: "SALE BY AMI" -> "NOT FOR SALE"
  * test mode, DIP SWITCH SETTING: new "bomb counts" line (1, 2, 3, 4, FULL,
    INFINITE; default 1): full bombs at the start and after each respawn
  * ship select: Start switches between Bond (Player 1) and Dyne (Player 2);
    the empty panel no longer shows credit text
  * coin, continue and name-entry countdown beep at 40% volume

No ROM data is stored in this script. Songs that Black Label doesn't use are
still present in its sound ROM, so a swap only re-points a music slot at them;
everything else is new code and text written into free space.

Usage:
    python showtime_patch.py <input> [-o OUTPUT_DIR] [--zip ROMSET.zip]
    python showtime_patch.py --list                  # show songs and slots

<input> is a folder or .zip (e.g. a MAME romset) containing ibarablk_u4 and u23.
Output defaults to ./output. Only the Python standard library is needed.
"""
import argparse
import hashlib
import sys
import time
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# What the default "Show Time" build changes.  Edit these, or use --swap /
# --boot-text on the command line, to make your own variant.
# ---------------------------------------------------------------------------
DEFAULT_SWAPS = [                    # (Black Label song to replace, song to play instead)
    ("Bonds of Steel", "Show Time"),
    ("Air Pollution", "Sky High"),
    ("The Family's Work", "Robot No28"),
]
DEFAULT_BOOT_TEXT = "2026/10/22 SHOW TIME"   # boot screen line (was "2006/xx/xx. MASTER VER.")

# Expected checksums -------------------------------------------------------
INPUTS = {   # name: (size, sha1)
    "ibarablk_u4": (2097152, "ac276f3955aa4dde2544af4912819a7ae6bcf8dd"),
    "u23":         (4194304, "0556e771cc02638bf8814315ba671c2d442594f1"),
}
DEFAULT_OUTPUTS = {   # sha1 of the result when the default settings are used
    "ibarablk_u4": "796b4540f1cd0be2dbc5c3238b2a74ba042e8b8d",   # crc32 531d55da
    "u23":         "51f6536b0845fc26f266761ae344992fb38ffee8",   # crc32 69403f24
}
UNPACKED_PROGRAM_SHA1 = "531fc52e0d84866bca8509f36a9c9e6319667bea"   # original, unpacked

# Songs: name -> (intro phrase/sequence, loop phrase/sequence).  The numbers are
# the same in Ibara and Ibara Kuro Black Label.  Single-phrase songs (Game Over,
# Mother Teresa) are not swappable here.
SONGS = {
    "Show Time":            (0x0F, 0x10),
    "Sky High":             (0x11, 0x12),
    "Like a Rolling Stone": (0x13, 0x14),
    "Endress Train":        (0x15, 0x16),
    "Robot No28":           (0x17, 0x18),
    "Rose Garden":          (0x19, 0x1A),
    "Ending":               (0x02, 0x03),
    "Guardian Angel":       (0x09, 0x0A),
    "Rose of Zeal":         (0x07, 0x08),
    "Ranking":              (0x04, 0x05),
    "Bonds of Steel":       (0x1B, 0x1C),
    "The Family's Work":    (0x1D, 0x1E),
    "Air Pollution":        (0x1F, 0x20),
}

# Black Label's own intro+loop songs (these have a title slot in the program)
BL_SLOTS = ["Sky High", "Like a Rolling Stone", "Endress Train", "Robot No28",
            "Rose Garden", "Ending", "Guardian Angel", "Rose of Zeal", "Ranking",
            "Bonds of Steel", "The Family's Work", "Air Pollution"]

# Locations ---------------------------------------------------------------
PACK_START, PACK_LIMIT = 0x51000, 0xFB4C0   # packed program area in ibarablk_u4 (CPU byte order)
RAM_BASE = 0x0C051000                       # where the packed program is unpacked to
TIMING_TABLES = (0x0C0C3A58, 0x0C0C3E58)    # u32 play time in ms, per sequence number
TITLE_AREA = (0x0C2069B4, 0x0C206A88)       # song-title list ("$Name\0...")
BOOT_LINES = (                              # boot text, one per region
    (0x0C0C4E08, b"    2006/xx/xx. MASTER VER.   "),
    (0x0C0C4F88, b"    200x/xx/xx. MASTER VER.   "),
)
WARNING_TEXT = [   # replaces the "for use in Japan only" screen (max 27 chars per line, 11 lines)
    "THIS PROJECT IS UNOFFICIAL",
    "AND IS NOT AFFILIATED WITH,",
    "ENDORSED BY, OR AUTHORIZED",
    "BY CAVE. ALL RIGHTS TO THE",
    "ORIGINAL GAME AND ITS",
    "ASSOCIATED INTELLECTUAL",
    "PROPERTY REMAIN WITH THEIR",
    "RESPECTIVE RIGHTS HOLDERS.",
    "",
    "HAVE FUN!!!",
]
WARNING_BLOCKS = ((0x0C0C4C68, 12), (0x0C0C4E28, 11))   # 32-byte lines (Japan / export boards; the
                                                          # export block's 12th slot is its boot line)
WARNING_FIRST = (b"   THIS GAME IS FOR USE IN    ", b"   ALL COUNTRIES EXCEPTING    ")
# Title screen: "SALE BY AMI" -> "NOT FOR SALE". The new text is one byte longer than the old
# slot, so it is stored in the (now blank) last line of the Japan warning block, behind a leading
# NUL so the warning screen still prints that line as empty, and the title code is re-pointed to it.
SALE_TEXT = b"NOT FOR SALE"
SALE_HOME = 0x0C0C4C68 + 32 * 11          # line 12 of the Japan warning block
SALE_PTR = (0x0C06A688, 0x0C173A60)       # literal-pool word used by the title print call (old value)
# --- DIP menu: "bomb counts" ----------------------------------------------------------
# The menu has a hidden line (index 12, "difficulty2", variable 0x0C23DEA4) that the game saves,
# loads and range-checks but never uses in play. It becomes "bomb counts" (0=1 ... 3=4, 4=FULL,
# 5=INFINITE). Menu indexes 12-14 are reordered so the lines read extend / player counts /
# bomb counts, and a small routine in unused RAM draws the extra line.
def _w(v): return v.to_bytes(4, "big")
BOMB_VAR = 0x0C23DEA4
BOMB_DRAW = 0x0C068920                    # existing "difficulty2" line-draw routine
TRAMPOLINE = 0x0C05B700                   # unused tail of a zero-filled table area
RANK_DRAW = 0x0C065EA0                    # "ranking save" line-draw routine
BOMB_VALUES = ["1", "2", "3", "4", "FULL", "INFINITE", "INFINITE", "INFINITE"]
MENU_EDITS = [   # (address, original bytes, new bytes)
    (0x0C0654B0, _w(RANK_DRAW), _w(TRAMPOLINE)),          # menu calls the routine instead of "ranking save"
    (0x0C06538A, b"\xe4\x0c", b"\xe4\x0e"),                # player counts: row 12 -> 14
    (0x0C06539A, b"\xe4\x0e", b"\xe4\x10"),                # extend: row 14 -> 16
    (0x0C068934, b"\x78\x0c", b"\x78\x0e"),                # value column lines up with player counts
    (0x0C173800, b"difficulty2\0", b"bomb counts\0"),      # label
    (0x0C1731FC + 4 * 12, _w(0x0C23DEA4) + _w(0x0C234BA8) + _w(0x0C239483),
                          _w(0x0C234BA8) + _w(0x0C239483) + _w(BOMB_VAR)),   # index -> variable
    (0x0C17325C + 12, bytes([7, 18, 7]), bytes([18, 7, 5])),                  # index -> max value
    (0x0C065B02, b"\x20\x40", b"\x20\x70"),                # default value 3 -> 0 (r7 = 0), i.e. "1"
] + [(t + 13, b"\x0b", b"\x0c") for t in (0x0C173298, 0x0C1732C0, 0x0C1732E8, 0x0C173310)] \
  + [(t + 11, b"\x0d", b"\x0c") for t in (0x0C1732AC, 0x0C1732D4, 0x0C1732FC, 0x0C173324)]
TRAMPOLINE_CODE = bytes.fromhex(
    "4f22" "d005" "400b" "0009"     # sts.l pr,@-r15 / mov.l RANK,r0 / jsr @r0 (row 10, col 3 from caller)
    "d004" "e40c" "400b" "e503"     # mov.l BOMB,r0 / mov #12,r4 / jsr @r0 / mov #3,r5
    "4f26" "000b" "0009" "0009"     # lds.l @r15+,pr / rts / nop
) + _w(RANK_DRAW) + _w(BOMB_DRAW)
BOMB_STRINGS = 0x0C17380C                 # 96 bytes of the old value strings, then the 8-entry table
BOMB_TABLE = 0x0C17386C

# --- Gameplay: apply "bomb counts" ----------------------------------------------------
# Player data is at 0x0C29D1D8 + player * 0x2A0; +0x25D = full bombs (max 4), +0x25E = bomb
# fragments (max 40). At game start and after each death the spawn code adds one full bomb.
# Hook 1 (spawn): after that, full bombs = max(normal result, setting + 1); FULL / INFINITE give
#   4 full bombs and 40 fragments.  Hook 2 (bomb): with INFINITE the full bomb is not used up.
# Each hook is a bsr to a 12-byte stub in nearby function padding that jumps to a routine in
# the unused RAM area.
SPAWN_CODE_AT, BOMB_CODE_AT = 0x0C05B680, 0x0C05B6C0
SPAWN_CODE = bytes.fromhex(
    "2290" "2370" "d109" "6010"     # mov.b r9,@r2 (full) / mov.b r7,@r3 (frags) / mov.l SET,r1 / mov.b @r1,r0
    "600c" "e104" "3012" "8907"     # extu.b r0,r0 / mov #4,r1 / cmp/hs r1,r0 / bt FULL
    "7001" "6120" "611c" "3102"     # add #1,r0 / mov.b @r2,r1 / extu.b r1,r1 / cmp/hs r0,r1
    "8900" "2200" "000b" "0009"     # bt (skip) / mov.b r0,@r2 / rts / nop
    "e104" "2210" "e128" "000b"     # FULL: mov #4,r1 / mov.b r1,@r2 / mov #40,r1 / rts
    "2310" "0009"                   #       mov.b r1,@r3 / pad
) + BOMB_VAR.to_bytes(4, "big")
BOMB_CODE = bytes.fromhex(
    "d505" "6050" "600c" "e505"     # mov.l SET,r5 / mov.b @r5,r0 / extu.b r0,r0 / mov #5,r5
    "3052" "8900" "2410" "9401"     # cmp/hs r5,r0 / bt (skip) / mov.b r1,@r4 (store full-1) / mov.w 0x2A0,r4
    "000b" "0009" "02a0" "0000"     # rts / nop / .word 0x2A0 / pad
) + BOMB_VAR.to_bytes(4, "big")
STUB = bytes.fromhex("d001" "402b" "0009" "0009")     # mov.l @(4,pc),r0 / jmp @r0 / nop / nop / .long target
GAME_EDITS = [   # (address, original bytes, new bytes)
    (0x0C06D216, bytes.fromhex("790122902370"), bytes.fromhex("b0cd" "7901" "0009")),   # spawn: bsr stub1 / add #1,r9
    (0x0C06D3B4, bytes.fromhex("0009" * 6), STUB + SPAWN_CODE_AT.to_bytes(4, "big")),
    (0x0C0736B6, bytes.fromhex("24109421"), bytes.fromhex("b035" "0009")),             # bomb: bsr stub2
    (0x0C073724, bytes.fromhex("0009" * 6), STUB + BOMB_CODE_AT.to_bytes(4, "big")),
]

# --- Ship select: Start switches to Dyne (the Player 2 character) ---------------------------
# A routine hooked into the control reader (0x0C060E54) runs every frame. The ship-select screen
# marks itself active every frame (hook at 0x0C0B8390, asm/select_mark.s). While it is active and
# the only player choosing is the one on the Player 1 controls, a new press of Player 1 Start
# swaps the two player blocks (each side keeps its own pilot bit), flips the choosing-side byte
# (0x0C239497) and toggles "Dyne mode" (0x0C05B4F0). That Start press is never passed to the
# game. In Dyne mode the Player 1 controls (and Start) drive the Player 2 side and the Player 2
# controls drive Player 1 (also during name entry). Dyne mode is cleared when a new game
# starts; outside a game (mode byte 0x0C2A6D64 != 6) and the ship select the controls are
# always normal.
# Sources: asm/p2_toggle.s, asm/select_mark.s, asm/new_game.s (assemble with tools/sh3asm.py)
INPUT_AT = 0x0C05B500
INPUT_STATE = 0x0C05B4F0                  # +0 Dyne mode flag, +1 previous Start state, +2 select active
MARK_AT = 0x0C05B600
MARK_CODE = bytes.fromhex("d202e1032210d202000b61220c05b4f20c238014")
NEWGAME_AT = 0x0C05B640                   # new game: Dyne mode off (asm/new_game.s)
NEWGAME_CODE = bytes.fromhex("e00017012f16d103e0018011e0002100000b61f60c05b4f0")
HADOU_AT = 0x0C05B660                     # INFINITE: the hadou gun spends nothing either (asm/hadou_keep.s)
HADOU_CODE = bytes.fromhex("d0036000880589002410000b000900090c23dea4")
KEEP_AT = 0x0C05B620                      # INFINITE: small bombs are not spent either (asm/bomb_keep.s)
KEEP_CODE = bytes.fromhex("2f26d2056220622ce004320660308b00e000000b62f600090c23dea4")
STUB_R1 = bytes.fromhex("d101" "412b" "0009" "0009")  # as STUB, but jumps via r1
INPUT_CODE = bytes.fromhex("d22c6620dd2cd23360208806890584d220088b02e000a039000984d2600c2008893270ff80d260d0600cdb246cb06ccc650375013c508b296063c810042984d16503604380d16063cb1066032448891b25588b19d21ad31be554355c64226832228223427204730445108bf7d2148427c9f78027d3138437cb08803760b0ca032b0060d0ca012d0060d0600c20088b03d40dd10ea00b0009d40cd10b6063c93088008904883089026063ca306603d008402b0009a40001240c05b4f00c2394970c29d1d80c29d478a4000126a40001340c060e580c2a6d64")
INPUT_EDITS = [
    (0x0C060DD4, bytes.fromhex("0009" * 6), STUB + INPUT_AT.to_bytes(4, "big")),
    (0x0C060E54, bytes.fromhex("d25d"), bytes.fromhex("afbe")),   # bra stub (delay slot: mov #16,r7)
    (0x0C060E58, bytes.fromhex("6620"), bytes.fromhex("0009")),   # start/coin byte now comes from the routine
    (0x0C060E5E, bytes.fromhex("7202"), bytes.fromhex("6243")),   # P1 port address from r4
    (0x0C060E78, bytes.fromhex("da56"), bytes.fromhex("6a13")),   # P2 port address from r1
    # ship select: no credit text on the empty panel ("PLEASE!", "INSERT COIN", "CREDIT n", free play)
    (0x0C06DA5C, bytes.fromhex("4a0b"), bytes.fromhex("0009")),
    (0x0C06DA68, bytes.fromhex("4a0b"), bytes.fromhex("0009")),
    (0x0C06DA82, bytes.fromhex("4a0b"), bytes.fromhex("0009")),
    (0x0C06DA9C, bytes.fromhex("400b"), bytes.fromhex("0009")),
    # ship select marks itself active every frame
    (0x0C0B8384, bytes.fromhex("0009" * 6), STUB_R1 + MARK_AT.to_bytes(4, "big")),
    (0x0C0B8390, bytes.fromhex("d26b6122"), bytes.fromhex("bff8" "0009")),   # bsr stub (redone in the routine)
    # INFINITE: with 40 small bombs the game would spend those; report 0 so a full bomb is used
    (0x0C0737B4, bytes.fromhex("0009" * 6), STUB + KEEP_AT.to_bytes(4, "big")),
    (0x0C0736A8, bytes.fromhex("73026030"), bytes.fromhex("b084" "7302")),   # bsr stub / add #2,r3
    # INFINITE: the hadou gun (bomb button held) uses its own copy of the bomb code
    (0x0C0737D0, bytes.fromhex("73026030"), bytes.fromhex("bff0" "7302")),   # bsr bomb_keep stub / add #2,r3
    (0x0C0737F4, bytes.fromhex("0009" * 6), STUB + HADOU_AT.to_bytes(4, "big")),
    (0x0C0737DA, bytes.fromhex("2410"), bytes.fromhex("b00b")),   # bsr stub (store only if not INFINITE)
    # new game: Dyne mode off
    (0x0C06AE44, bytes.fromhex("0009" * 6), STUB + NEWGAME_AT.to_bytes(4, "big")),
    (0x0C06A7B4, bytes.fromhex("1701"), bytes.fromhex("b346")),   # bsr stub (redone in the routine)
]

# --- Sound: countdown beep at half volume ----------------------------------------------
# Effect 0x5C ("continue") is the beep of the coin, continue and name-entry countdowns. Its
# default volume in the effect volume table (0x0C206824 + effect) is 0xFC; the level is linear
# (measured in MAME). 0x65 = 40% (half, then another 20% lower). The laughs (0x81, 0x97) are
# separate effects.
BEEP_VOLUME = (0x0C206824 + 0x5C, 0xFC, 0x65)

BOOT_DATE_CALLS = (0x0C06BC82, 0x0C06BC8E)  # "print clock month/day" calls -> NOP
ROMSET_EXTRAS = ("ibarablk_u2", "u24")      # unchanged romset files copied by --zip
OUT_NAMES = {"ibarablk_u4": "ibarashow_u4", "u23": "ibarashow_u23"}   # output file names
SEQ_TABLE = 0x400                           # u23 sequence pointer table (sound-chip byte order)

# ---------------------------------------------------------------------------
# LZSS codec used by the game's boot loader
# ---------------------------------------------------------------------------
MAXD, MINL, MAXL = 2047, 3, 34


def lz_decompress(buf: bytes, base: int):
    size = int.from_bytes(buf[base:base + 4], "big")
    count = int.from_bytes(buf[base + 4:base + 8], "big")
    fl = base + 12
    dp = base + int.from_bytes(buf[base + 8:base + 12], "big")
    out = bytearray()
    bits = flag = 0
    for _ in range(count):
        if bits == 0:
            flag = buf[fl]; fl += 1; bits = 8
        if flag & 0x80:
            w = buf[dp] << 8 | buf[dp + 1]; dp += 2
            start = len(out) - (w >> 5)
            for k in range((w & 0x1F) + 3):
                out.append(out[start + k])
        else:
            out.append(buf[dp]); dp += 1
        flag = (flag << 1) & 0xFF
        bits -= 1
    if len(out) != size:
        raise ValueError("corrupt packed program")
    return bytes(out)


def lz_compress(d: bytes) -> bytes:
    """Optimal-parse LZSS. Deterministic, so the default build is reproducible."""
    n = len(d)
    head = [-1] * 0x40000
    prev = [-1] * n
    bl = [0] * n
    bd = [0] * n
    for i in range(n):
        best = bdist = 0
        if i + MINL <= n:
            h = ((d[i] << 10) ^ (d[i + 1] << 5) ^ d[i + 2]) & 0x3FFFF
            m = n - i if n - i < MAXL else MAXL
            j = head[h]
            while j >= 0 and i - j <= MAXD:
                if best < m and d[j + best] == d[i + best]:
                    l = 0
                    while l < m and d[j + l] == d[i + l]:
                        l += 1
                    if l > best:
                        best, bdist = l, i - j
                        if l == MAXL:
                            break
                j = prev[j]
            prev[i] = head[h]
            head[h] = i
        if best >= MINL:
            bl[i], bd[i] = best, bdist
    cost = [0] * (n + 1)
    choice = [0] * n
    for i in range(n - 1, -1, -1):
        c, ch = 9 + cost[i + 1], 0
        for L in range(MINL, bl[i] + 1):
            cc = 17 + cost[i + L]
            if cc < c:
                c, ch = cc, L
        cost[i], choice[i] = c, ch
    flags, data = bytearray(), bytearray()
    items = bit = i = 0
    while i < n:
        if bit == 0:
            flags.append(0)
        L = choice[i]
        if L:
            flags[-1] |= 0x80 >> bit
            w = (bd[i] << 5) | (L - 3)
            data += bytes((w >> 8, w & 0xFF))
            i += L
        else:
            data.append(d[i])
            i += 1
        bit = (bit + 1) & 7
        items += 1
    return (n.to_bytes(4, "big") + items.to_bytes(4, "big")
            + (12 + len(flags)).to_bytes(4, "big") + bytes(flags) + bytes(data))


# ---------------------------------------------------------------------------
def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def wordswap(b: bytes) -> bytearray:
    """Swap each pair of bytes (ROM file order <-> CPU / sound-chip order)."""
    out = bytearray(len(b))
    out[0::2], out[1::2] = b[1::2], b[0::2]
    return out


def song(name: str):
    for k, v in SONGS.items():
        if k.lower() == name.strip().lower():
            return k, v
    sys.exit(f"error: unknown song '{name}'. Use --list to see the names.")


def find_inputs(src: Path) -> dict:
    """Return {name: bytes} for the needed files, matched by name or by hash."""
    by_hash = {h: n for n, (_, h) in INPUTS.items()}
    sizes = {s for s, _ in INPUTS.values()}
    found = {}

    def offer(fname, read):
        base = fname.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in INPUTS and base not in found:
            found[base] = read()
            return
        data = read()
        name = by_hash.get(sha1(data))
        if name and name not in found:
            found[name] = data

    if src.is_dir():
        for f in sorted(src.rglob("*")):
            if f.is_file() and f.stat().st_size in sizes:
                offer(f.name, f.read_bytes)
    elif zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for i in z.infolist():
                if not i.is_dir() and i.file_size in sizes:
                    offer(i.filename, lambda i=i: z.read(i))
    else:
        sys.exit(f"error: {src} is not a folder or zip file")
    return found


def title_fields(prog: bytes):
    """Map title -> (offset in unpacked program, field length)."""
    lo, hi = TITLE_AREA[0] - RAM_BASE, TITLE_AREA[1] - RAM_BASE
    starts = [i for i in range(lo, hi) if prog[i] == 0x24 and (i == lo or prog[i - 1] == 0)]
    fields = {}
    for k, s in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else hi
        name = prog[s + 1:prog.index(b"\0", s)].decode("latin-1")
        fields[name] = (s, end - s)
    return fields


def apply_extras(orig: bytes, prog: bytearray):
    """Fixed Show Time changes: warning screen, title text, DIP "bomb counts", bomb rules,
    Dyne toggle on ship select, countdown beep volume. Every target is checked first."""
    # warning screen
    for (addr, lines), first in zip(WARNING_BLOCKS, WARNING_FIRST):
        o = addr - RAM_BASE
        if orig[o:o + 30] != first:
            sys.exit("error: warning text not found where expected")
        for k in range(lines):
            text = WARNING_TEXT[k] if k < len(WARNING_TEXT) else ""
            prog[o + 32 * k:o + 32 * k + 30] = ("   " + text).ljust(30).encode("ascii")

    # title screen: "SALE BY AMI" -> "NOT FOR SALE"
    o = SALE_HOME - RAM_BASE
    prog[o:o + 32] = (b"\0" + b" " * 15 + SALE_TEXT).ljust(32, b"\0")
    po = SALE_PTR[0] - RAM_BASE
    if orig[po:po + 4] != SALE_PTR[1].to_bytes(4, "big"):
        sys.exit("error: title credit pointer not found where expected")
    prog[po:po + 4] = (SALE_HOME + 16).to_bytes(4, "big")

    # DIP menu: bomb counts
    for addr, old, new in MENU_EDITS:
        o = addr - RAM_BASE
        if orig[o:o + len(old)] != old:
            sys.exit(f"error: menu data not found where expected ({addr:08X})")
        prog[o:o + len(new)] = new
    o = TRAMPOLINE - RAM_BASE
    if any(orig[o:o + 0x34]):
        sys.exit("error: free space for the menu routine is not empty")
    prog[o:o + len(TRAMPOLINE_CODE)] = TRAMPOLINE_CODE
    blob, ptrs = bytearray(), {}
    for v in dict.fromkeys(BOMB_VALUES):
        ptrs[v] = BOMB_STRINGS + len(blob)
        blob += v.encode("ascii") + b"\0"
        blob += b"\0" * (-len(blob) % 4)
    o = BOMB_STRINGS - RAM_BASE
    if orig[o:o + 12] != b"UNFORGETABLE":
        sys.exit("error: difficulty2 values not found where expected")
    prog[o:o + 96] = bytes(blob).ljust(96, b"\0")
    o = BOMB_TABLE - RAM_BASE
    prog[o:o + 32] = b"".join(_w(ptrs[v]) for v in BOMB_VALUES)

    # gameplay: bomb counts
    for at, code in ((SPAWN_CODE_AT, SPAWN_CODE), (BOMB_CODE_AT, BOMB_CODE)):
        o = at - RAM_BASE
        if any(orig[o:o + len(code)]):
            sys.exit("error: free space for the bomb routines is not empty")
        prog[o:o + len(code)] = code
    for addr, old, new in GAME_EDITS:
        o = addr - RAM_BASE
        if orig[o:o + len(old)] != old:
            sys.exit(f"error: game code not found where expected ({addr:08X})")
        prog[o:o + len(new)] = new

    # ship select: P2 toggle
    o = INPUT_STATE - RAM_BASE
    if any(orig[o:o + (INPUT_AT - INPUT_STATE) + len(INPUT_CODE)]):
        sys.exit("error: free space for the select-screen routine is not empty")
    o = INPUT_AT - RAM_BASE
    prog[o:o + len(INPUT_CODE)] = INPUT_CODE
    for at, code in ((MARK_AT, MARK_CODE), (KEEP_AT, KEEP_CODE), (NEWGAME_AT, NEWGAME_CODE),
                     (HADOU_AT, HADOU_CODE)):
        o = at - RAM_BASE
        if any(orig[o:o + len(code)]):
            sys.exit("error: free space for the select/bomb routines is not empty")
        prog[o:o + len(code)] = code
    for addr, old, new in INPUT_EDITS:
        o = addr - RAM_BASE
        if orig[o:o + len(old)] != old:
            sys.exit(f"error: control code not found where expected ({addr:08X})")
        prog[o:o + len(new)] = new

    # sound: countdown beep volume
    addr, old, new = BEEP_VOLUME
    if orig[addr - RAM_BASE] != old:
        sys.exit("error: effect volume table not found where expected")
    prog[addr - RAM_BASE] = new



def build(u4: bytes, u23: bytes, swaps, boot_text):
    # --- sound ROM: re-point sequences --------------------------------------
    snd = wordswap(u23)
    seq_entry = lambda n: SEQ_TABLE + 4 * n
    orig_snd = bytes(snd)
    for old, new in swaps:
        (_, (oi, ol)), (_, (ni, nl)) = song(old), song(new)
        for dst, src in ((oi, ni), (ol, nl)):
            snd[seq_entry(dst):seq_entry(dst) + 4] = orig_snd[seq_entry(src):seq_entry(src) + 4]
    out23 = bytes(wordswap(snd))

    # --- program: unpack ----------------------------------------------------
    cpu = wordswap(u4)
    prog = bytearray(lz_decompress(cpu, PACK_START))
    if sha1(prog) != UNPACKED_PROGRAM_SHA1:
        sys.exit("error: unexpected program contents (not the expected ibarablk_u4)")
    orig = bytes(prog)

    # play times
    for t in TIMING_TABLES:
        o = t - RAM_BASE
        get = lambda n: orig[o + 4 * n:o + 4 * n + 4]
        for old, new in swaps:
            (_, (oi, ol)), (_, (ni, nl)) = song(old), song(new)
            prog[o + 4 * oi:o + 4 * oi + 4] = get(ni)
            prog[o + 4 * ol:o + 4 * ol + 4] = get(nl)

    # titles
    fields = title_fields(orig)
    for old, new in swaps:
        old, _ = song(old)
        new, _ = song(new)
        if old not in fields:
            sys.exit(f"error: '{old}' is not a Black Label song slot")
        off, size = fields[old]
        text = b"$" + new.encode("latin-1")
        if len(text) + 1 > size:
            text = text[:size - 1]
            print(f"  note: title '{new}' shortened to '{text[1:].decode()}' to fit the '{old}' slot")
        prog[off:off + size] = text.ljust(size, b"\0")

    # boot text
    if boot_text is not None:
        line = ("    " + boot_text).encode("latin-1")
        if len(line) > 30:
            sys.exit("error: boot text is limited to 26 characters")
        for addr, expect in BOOT_LINES:
            o = addr - RAM_BASE
            if orig[o:o + 30] != expect:
                sys.exit("error: boot text not found where expected")
            prog[o:o + 30] = line.ljust(30)
        for addr in BOOT_DATE_CALLS:
            o = addr - RAM_BASE
            if orig[o:o + 2] != b"\x49\x0b":
                sys.exit("error: boot date code not found where expected")
            prog[o:o + 2] = b"\x00\x09"   # nop: keep the clock date from overwriting the text

    apply_extras(orig, prog)

    # --- program: repack ----------------------------------------------------
    print("  repacking program (takes about a minute)...", flush=True)
    t0 = time.time()
    packed = lz_compress(bytes(prog))
    if PACK_START + len(packed) > PACK_LIMIT:
        sys.exit("error: repacked program does not fit")
    cpu[PACK_START:PACK_LIMIT] = packed + bytes(PACK_LIMIT - PACK_START - len(packed))
    if lz_decompress(cpu, PACK_START) != bytes(prog):
        sys.exit("error: repack verification failed")
    print(f"  repacked in {time.time() - t0:.0f}s, verified", flush=True)
    return bytes(wordswap(cpu)), out23


def make_ips(a: bytes, b: bytes) -> bytes:
    """Standard IPS patch turning a into b (for Flips, Lunar IPS and similar tools)."""
    out, i, n = bytearray(b"PATCH"), 0, len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < n and a[i] != b[i] and i - start < 0xFFFF:
            i += 1
        if start == 0x454F46:            # an IPS record may not start at "EOF"
            start -= 1
        out += start.to_bytes(3, "big") + (i - start).to_bytes(2, "big") + b[start:i]
    return bytes(out + b"EOF")


def list_songs():
    print("Black Label songs that can be replaced (--swap 'OLD=NEW'):")
    for name in BL_SLOTS:
        i, l = SONGS[name]
        print(f"  {name:22s} slots {i:02X} (intro) / {l:02X} (loop)")
    print("\nSongs that can be played instead:")
    for name, (i, l) in SONGS.items():
        print(f"  {name:22s} sequences {i:02X} / {l:02X}")
    print("\nDefault Show Time build:")
    for old, new in DEFAULT_SWAPS:
        print(f"  {old}  ->  {new}")
    print(f"  boot text: {DEFAULT_BOOT_TEXT!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, nargs="?", help="folder or .zip with ibarablk_u4 and u23")
    ap.add_argument("-o", "--output", type=Path, default=Path("output"),
                    help="output folder (default: ./output)")
    ap.add_argument("--zip", type=Path, metavar="ROMSET.zip",
                    help="also write a complete romset zip (other files are copied from the input)")
    ap.add_argument("--ips", type=Path, metavar="DIR",
                    help="also write IPS patches (original -> result) to DIR")
    ap.add_argument("--swap", action="append", metavar="'OLD=NEW'",
                    help="replace Black Label song OLD with NEW (repeatable; replaces the default swaps)")
    ap.add_argument("--boot-text", help=f"boot screen text (default: '{DEFAULT_BOOT_TEXT}')")
    ap.add_argument("--keep-boot-text", action="store_true", help="leave the boot text unchanged")
    ap.add_argument("--list", action="store_true", help="show song slots and exit")
    ap.add_argument("--force", action="store_true",
                    help="patch even if an input checksum does not match")
    args = ap.parse_args()

    if args.list:
        list_songs()
        return
    if args.input is None:
        ap.error("input is required")

    inputs = find_inputs(args.input)
    missing = [n for n in INPUTS if n not in inputs]
    if missing:
        sys.exit(f"error: {', '.join(missing)} not found in {args.input}")
    for name, (size, h) in INPUTS.items():
        if sha1(inputs[name]) != h:
            print(f"[bad dump] {name}: sha1 {sha1(inputs[name])} (expected {h})")
            if not args.force:
                sys.exit(1)

    swaps = DEFAULT_SWAPS
    if args.swap:
        swaps = []
        for s in args.swap:
            if "=" not in s:
                sys.exit(f"error: --swap needs OLD=NEW, got '{s}'")
            old, new = s.split("=", 1)
            old, new = song(old)[0], song(new)[0]
            if old not in BL_SLOTS:
                sys.exit(f"error: '{old}' is not a replaceable Black Label song (see --list)")
            swaps.append((old, new))
    boot = None if args.keep_boot_text else (args.boot_text or DEFAULT_BOOT_TEXT)
    is_default = swaps == DEFAULT_SWAPS and boot == DEFAULT_BOOT_TEXT

    src_dir = args.input.resolve() if args.input.is_dir() else args.input.resolve().parent
    if args.input.is_dir() and args.output.resolve() == src_dir:
        sys.exit("error: output folder is the input folder - this would overwrite "
                 "your original files. Choose another folder with -o.")

    for old, new in swaps:
        print(f"  {old}  ->  {new}")
    print(f"  boot text: {boot!r}" if boot else "  boot text: unchanged")
    out_u4, out_u23 = build(inputs["ibarablk_u4"], inputs["u23"], swaps, boot)
    results = {"ibarablk_u4": out_u4, "u23": out_u23}

    if is_default:
        for name, data in results.items():
            if sha1(data) != DEFAULT_OUTPUTS[name]:
                sys.exit(f"[failed] {name}: result sha1 {sha1(data)} "
                         f"(expected {DEFAULT_OUTPUTS[name]})")
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in results.items():
        out = args.output / OUT_NAMES[name]
        out.write_bytes(data)
        tag = "verified" if is_default else "custom build"
        print(f"[ok] {out}  sha1 {sha1(data)}  ({tag})")

    if args.ips:
        args.ips.mkdir(parents=True, exist_ok=True)
        for name, data in results.items():
            (args.ips / f"{name}.ips").write_bytes(make_ips(inputs[name], data))
            print(f"[ok] {args.ips / (name + '.ips')}")

    if args.zip:
        if args.zip.resolve() == args.input.resolve():
            sys.exit("error: --zip would overwrite the input zip")
        with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in results.items():
                zout.writestr(OUT_NAMES[name], data)
            copied = 0
            if zipfile.is_zipfile(args.input):
                with zipfile.ZipFile(args.input) as zin:
                    for i in zin.infolist():
                        base = i.filename.rsplit("/", 1)[-1]
                        if not i.is_dir() and base.lower() not in results:
                            zout.writestr(base, zin.read(i)); copied += 1
            elif args.input.is_dir():
                for extra in ROMSET_EXTRAS:
                    f = args.input / extra
                    if f.is_file():
                        zout.write(f, extra); copied += 1
        print(f"[ok] {args.zip}  (2 patched + {copied} copied files)")


if __name__ == "__main__":
    main()
