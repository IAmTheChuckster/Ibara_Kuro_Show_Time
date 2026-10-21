#!/usr/bin/env python3
"""Build the Ibara Kuro "Show Time" ROMs from your own Ibara Kuro Black Label dump.

    ibarablk_u4  ->  ibarablk_u4  (Show Time version: play times, titles, boot text)
    u23          ->  u23          (Show Time version: sound-chip sequence table)

No ROM data is stored in this script. Every change is made from data that is
already in your dump: songs that Black Label doesn't use are still present in
its sound ROM, so a swap only re-points a music slot at them.

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
DEFAULT_BOOT_TEXT = "2026/10/12 SHOW TIME"   # boot screen line (was "2006/xx/xx. MASTER VER.")

# Expected checksums -------------------------------------------------------
INPUTS = {   # name: (size, sha1)
    "ibarablk_u4": (2097152, "ac276f3955aa4dde2544af4912819a7ae6bcf8dd"),
    "u23":         (4194304, "0556e771cc02638bf8814315ba671c2d442594f1"),
}
DEFAULT_OUTPUTS = {   # sha1 of the result when the default settings are used
    "ibarablk_u4": "82403646d72070ea3207d464a25fa8c2ff90f943",   # crc32 07243591
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
BOOT_DATE_CALLS = (0x0C06BC82, 0x0C06BC8E)  # "print clock month/day" calls -> NOP
ROMSET_EXTRAS = ("ibarablk_u2", "u24")      # unchanged romset files copied by --zip
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
        (args.output / name).write_bytes(data)
        tag = "verified" if is_default else "custom build"
        print(f"[ok] {args.output / name}  sha1 {sha1(data)}  ({tag})")

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
                zout.writestr(name, data)
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
