# Ibara Kuro Show Time: project spec for Claude

This file describes the whole project so it can be rebuilt from scratch in an empty repo.
It is a fan patch for the Cave CV1000 (CV1k) arcade game **Ibara Kuro Black Label
(Japan, 2006/02/06 MASTER VER.)**, MAME set `ibarablk`. The repo holds only source, tools
and notes. **Never commit ROM data**; users patch their own dump.

## Working rules

- Every change to `index.html` is a new web patcher build: increment `const BUILD` in
  `index.html` (shown in the status column as "Matches Build N" and in the line
  "Build N: built and verified against the Show Time checksums.") and add a row to
  `BUILDS.md` (build, date, commit, changes) in the same commit. Current build: 10.
- The Python script and the web page must produce byte-identical output. After changing
  `apply_extras()` in `patch.py`, regenerate `FIXED_EDITS` in `index.html` with
  `python tools/gen_web_extras.py <ibarablk.zip>` and update the expected checksums in both.
- After changing any routine, check `python tools/check_asm.py` (asm sources vs bytes in `patch.py`).
- Testing is done by the user in MAME 0.289 and on MiSTer (CV1k core by Raki / ika-musume).
- `.gitignore`: `ibarablk_u4`, `u23`, `ibarablk_u2`, `u24`, `*.zip`, `*.ips`, `output/`, `__pycache__/`.

## Repo layout

| Path | What it is |
|---|---|
| `patch.py` | Command-line patcher, Python 3.8+ standard library only |
| `index.html` | Single-file browser patcher, published with GitHub Pages |
| `mister/Ibara Kuro Show Time.mra` | MiSTer CV1k MRA for the complete romset |
| `asm/*.s` | SH-3 sources of every new routine |
| `tools/sh3asm.py` | Tiny SH-3 assembler: `assemble(base, src) -> bytes` (labels, `.long`, `.word`, `.align 4` pads with 0x0009, `mov.l/mov.w @label,Rn` PC-relative) |
| `tools/check_asm.py` | Assembles each `asm/*.s` at its address and compares with the bytes in `patch.py`; prints `name ok` |
| `tools/gen_web_extras.py` | Unpacks the program, runs `apply_extras()`, prints only changed bytes as `[address, "hex"]` runs for `FIXED_EDITS` |
| `README.md`, `BUILDS.md` | User docs and web patcher build log |

## Inputs and outputs

| File | Size | CRC32 | SHA-1 | Role |
|---|---|---|---|---|
| `ibarablk_u4` (in) | 2 MiB | `ee1f1f77` | `ac276f3955aa4dde2544af4912819a7ae6bcf8dd` | SH-3 program |
| `u23` (in) | 4 MiB | `a436bb22` | `0556e771cc02638bf8814315ba671c2d442594f1` | YMZ770 sound ROM 0 |
| `ibarashow_u4` (out) | | `59721266` | `e7007860c48e55fd0e9c9dee8a88e868d333fe71` | |
| `ibarashow_u23` (out) | | `69403f24` | `51f6536b0845fc26f266761ae344992fb38ffee8` | |
| `ibarablk_u2` (copied) | 138412032 | `5e46be44` | | NAND graphics, unchanged |
| `u24` (copied) | 4 MiB | `d11ab6b6` | | sound ROM 1, unchanged |

Unpacked original program SHA-1: `531fc52e0d84866bca8509f36a9c9e6319667bea`.
Inputs are found in a folder or zip by file name, or by SHA-1 if renamed.
The complete romset zip is `ibarashow.zip` = the two outputs + `ibarablk_u2` + `u24`.

## How the ROMs are stored

- ROM files are byte-swapped in 16-bit words relative to CPU / sound-chip order; `wordswap()` both ways.
- The program in `u4` (CPU order) is LZSS-packed at `PACK_START = 0x51000`, must end before
  `PACK_LIMIT = 0xFB4C0`, and unpacks to RAM at `RAM_BASE = 0x0C051000`. All addresses
  below are RAM addresses; file offset in the unpacked program = address - RAM_BASE.
- LZSS header: u32 BE unpacked size, u32 item count, u32 data offset (from base); flag bytes
  start at base+12, MSB first. Flag 1 = 16-bit BE word `w`: distance `w >> 5` (max 2047),
  length `(w & 0x1F) + 3` (3..34). Flag 0 = literal byte.
- Repacking uses a deterministic optimal parse (hash chains over 3-byte keys, 18-bit hash
  `(d0<<10 ^ d1<<5 ^ d2) & 0x3FFFF`, cost 9 bits per literal and 17 per match, DP from the end)
  so the default build is reproducible. Pad the rest of the pack area with zeros and verify by
  unpacking again. JS port must give identical bytes.
- `u23` sequence pointer table at `0x400` (sound-chip order), 4 bytes per sequence number.

## What the patch changes

### Music (u23 + program)
Swap Black Label songs to the loop-one Ibara songs that are still in the sound ROM.
Song = (intro seq, loop seq):

Show Time 0F/10, Sky High 11/12, Like a Rolling Stone 13/14, Endress Train 15/16,
Robot No28 17/18, Rose Garden 19/1A, Ending 02/03, Guardian Angel 09/0A, Rose of Zeal 07/08,
Ranking 04/05, Bonds of Steel 1B/1C, The Family's Work 1D/1E, Air Pollution 1F/20.

Default swaps: Bonds of Steel -> Show Time, Air Pollution -> Sky High, The Family's Work -> Robot No28.
For each swap: copy the new song's seq table entries over the old one's (both intro and loop);
copy play times in both timing tables `0x0C0C3A58`, `0x0C0C3E58` (u32 ms per seq number);
rewrite the title in the title list `0x0C2069B4..0x0C206A88` (`$Name\0` fields, keep field size,
truncate if too long). Black Label title slots: Sky High, Like a Rolling Stone, Endress Train,
Robot No28, Rose Garden, Ending, Guardian Angel, Rose of Zeal, Ranking, Bonds of Steel,
The Family's Work, Air Pollution.

### Boot line
`"    " + "2026/10/29 SHOW TIME"` padded to 30 bytes at `0x0C0C4E08` (was `"    2006/xx/xx. MASTER VER.   "`)
and `0x0C0C4F88` (was `"    200x/xx/xx. MASTER VER.   "`). NOP (`0009`) the clock-date print
calls at `0x0C06BC82` and `0x0C06BC8E` (originally `490b`). Max 26 characters of text.

### Warning screen
Two blocks of 32-byte lines: Japan `0x0C0C4C68` (12 lines, starts `"   THIS GAME IS FOR USE IN    "`),
export `0x0C0C4E28` (11 lines, starts `"   ALL COUNTRIES EXCEPTING    "`). Each line =
`"   " + text` padded to 30. Text (max 27 chars per line):
THIS PROJECT IS UNOFFICIAL / AND IS NOT AFFILIATED WITH, / ENDORSED BY, OR AUTHORIZED /
BY CAVE. ALL RIGHTS TO THE / ORIGINAL GAME AND ITS / ASSOCIATED INTELLECTUAL /
PROPERTY REMAIN WITH THEIR / RESPECTIVE RIGHTS HOLDERS. / (blank) / HAVE FUN!!!

### Title screen
`SALE BY AMI` -> `NOT FOR SALE`. The new text is longer than the slot, so write
`"\0" + 15 spaces + "NOT FOR SALE"` (padded to 32 with NUL) into line 12 of the Japan warning
block (`0x0C0C4C68 + 32*11`) and change the literal pool word at `0x0C06A688` from
`0x0C173A60` to that line + 16.

### Test mode, DIP SWITCH SETTING: "bomb counts"
The hidden "difficulty2" line (menu index 12, variable `0x0C23DEA4`, saved but unused) becomes
**bomb counts**: 0..3 = 1..4, 4 = FULL, 5 = INFINITE, default 0.
- `0x0C0654B0`: literal `0x0C065EA0` (ranking-save draw) -> `0x0C05B700` (asm/menu_line.s: calls
  ranking save, then the difficulty2 draw routine `0x0C068920` with r4=12, r5=3).
- `0x0C06538A` `e40c`->`e40e` (player counts row 12->14); `0x0C06539A` `e40e`->`e410` (extend row 14->16);
  `0x0C068934` `780c`->`780e` (value column).
- `0x0C173800` label `difficulty2\0` -> `bomb counts\0`.
- Index->variable table `0x0C1731FC`: entries 12..14 `0C23DEA4 0C234BA8 0C239483` ->
  `0C234BA8 0C239483 0C23DEA4`. Index->max table `0x0C17325C`: bytes 12..14 `07 12 07` -> `12 07 05`.
- `0x0C065B02` `2040`->`2070` (default value 0).
- Cursor-order tables `0x0C173298`, `0x0C1732C0`, `0x0C1732E8`, `0x0C173310`: byte +13 `0b`->`0c`;
  `0x0C1732AC`, `0x0C1732D4`, `0x0C1732FC`, `0x0C173324`: byte +11 `0d`->`0c`.
- Value strings: overwrite 96 bytes at `0x0C17380C` (starts `UNFORGETABLE`) with
  `1`,`2`,`3`,`4`,`FULL`,`INFINITE` (NUL-terminated, 4-byte aligned), then the 8-entry pointer
  table at `0x0C17386C`: 1,2,3,4,FULL,INFINITE,INFINITE,INFINITE.

### Gameplay: bomb counts
Player data at `0x0C29D1D8 + player*0x2A0`; +0x25D full bombs (max 4), +0x25E small bombs (max 40).
Hooks are a `bsr` to a 16-byte stub in function padding (`d001 402b 0009 0009` + `.long target`,
or `d101 412b ...` to jump via r1) that jumps into unused zero-filled RAM at `0x0C05B4F0..0x0C05B740`.
Every target is checked against its original bytes, and free space is checked to be zero.
- Spawn (`asm/bomb_spawn.s` @ `0x0C05B680`, hook `0x0C06D216`, stub `0x0C06D3B4`): full = max(normal, setting+1);
  FULL/INFINITE give 4 full and 40 small.
- Bomb use (`asm/bomb_use.s` @ `0x0C05B6C0`, hook `0x0C0736B6`, stub `0x0C073724`): INFINITE keeps the full bomb.
- Small bombs (`asm/bomb_keep.s` @ `0x0C05B620`, hooks `0x0C0736A8` and `0x0C0737D0`, stub `0x0C0737B4`):
  INFINITE reports 0 small bombs so the never-spent full bomb is used.
- Hadou gun (`asm/hadou_keep.s` @ `0x0C05B660`, hook `0x0C0737DA`, stub `0x0C0737F4`): INFINITE spends nothing.

### Ship select: Start toggles Dyne
In a one-player game, P1 Start on ship select switches between Bond (P1) and Dyne (P2);
P1 controls then fly the chosen side, including name entry. The press is not passed to the game.
- State at `0x0C05B4F0`: +0 Dyne flag, +1 Start held last frame, +2 select-active counter.
- `asm/p2_toggle.s` @ `0x0C05B500`: entered from the control reader (`0x0C060E54` `d25d`->`afbe`
  bra to stub `0x0C060DD4`), returns to `0x0C060E58` with r6 = start/coin byte, r4 = P1 port,
  r1 = P2 port. Also `0x0C060E58` `6620`->`0009`, `0x0C060E5E` `7202`->`6243`, `0x0C060E78` `da56`->`6a13`.
  Swaps the player blocks (each keeps its pilot bit), flips choosing side `0x0C239497`, toggles
  Dyne mode. Only active in game mode (mode byte `0x0C2A6D64` == 6) or on ship select.
- `asm/select_mark.s` @ `0x0C05B600`: hook `0x0C0B8390` (`d26b6122` -> `bff8 0009`), stub `0x0C0B8384` (via r1);
  sets select-active = 3 each frame.
- `asm/new_game.s` @ `0x0C05B640`: hook `0x0C06A7B4` (`1701`->`b346`), stub `0x0C06AE44`; Dyne off, Start counted as held.
- `asm/test_mode.s` @ `0x0C05B6E0`: hook `0x0C062808` (`d879db7a` -> `b0d4 0009`), stub `0x0C0629B4`; Dyne off in test mode.
- Empty panel credit text removed: NOP (`0009`) the calls at `0x0C06DA5C`, `0x0C06DA68`,
  `0x0C06DA82` (`4a0b`) and `0x0C06DA9C` (`400b`).

### Sound
Countdown beep (effect 0x5C) volume in the effect volume table `0x0C206824 + 0x5C`: `0xFC` -> `0x65` (40%).
Laughs (0x81, 0x97) are separate and unchanged.

## patch.py

`python patch.py <folder|zip> [-o OUTPUT_DIR] [--zip ROMSET.zip] [--ips DIR] [--swap 'OLD=NEW' ...] [--boot-text TEXT | --keep-boot-text] [--force] [--list]`.
Default output `./output` with `ibarashow_u4` and `ibarashow_u23`; `--ips DIR` also writes IPS patches.
Prints "verified" when the default settings reproduce the expected SHA-1s, otherwise "custom build".
Structure: constants at the top, `lz_decompress`, `lz_compress`, `wordswap`, `find_inputs`,
`title_fields`, `apply_extras(orig, prog)` (all fixed changes above), `build(u4, u23, swaps, boot_text)`
(songs, play times, titles, boot text, `apply_extras`, repack), `make_ips`, `list_songs`, `main`.

## index.html (web patcher)

Single file, no build step, no external scripts; fonts from Google Fonts (Saira Condensed,
IBM Plex Sans, IBM Plex Mono). Narrow column, crimson accent (`#a3123c`, dark `#ff5c86`),
light and dark themes via CSS tokens. Everything runs locally; nothing is uploaded.

1. **Load your romset**: drop zone / file picker for `ibarablk.zip` (or loose files). Own zip
   reader (stored + deflate via `DecompressionStream("deflate-raw")`).
2. **Check files**: table of name, CRC32, SHA-1, status for each input; `ibarablk_u2`/`u24`
   are needed only for the complete romset. Optional song swaps and boot text under a `<details>`.
3. **Download Show Time**: builds automatically in a Web Worker with a progress bar, then shows
   `ibarashow_u4` / `ibarashow_u23` with CRC32, SHA-1 and a pill: "Matches Build N" (ok),
   "Custom build" (warn) or "Mismatch" (bad). One row of two buttons:
   **Download complete romset (ibarashow.zip)** (primary; disabled unless `ibarablk_u2` and
   `u24` with the right CRCs were in the zip) and **Download Ibara Kuro Show Time.mra** (secondary).
   Hint text explains both. Zip writer uses `CompressionStream("deflate-raw")`; extras are copied
   from the input zip without recompressing.

The JS core is a straight port of `patch.py`; the fixed changes are carried as `FIXED_EDITS`
(only new bytes, generated by `tools/gen_web_extras.py`), applied after the unpacked program's
SHA-1 is checked. The MRA is generated in the page (`mraText()`) from the same name/CRC tables.

## MiSTer MRA

`<name>Ibara Kuro Black Label (2026/10/29 SHOW TIME)</name>`, setname `ibara_showtime`, rbf
`ikacore_CV1k`, zip `ibarashow.zip`, DDR3-direct format:
- rom index 1, address `0x34400000`: `ibarablk_u2` (5e46be44)
- rom index 2, address `0x3C800000`: `ibarashow_u23` (69403f24) + 0x400000 zero bytes + `u24` (d11ab6b6) + 0x400000 zero bytes
- nvram index 3, size 135680
- rom index 0 (last): `ibarashow_u4` (59721266) listed twice (A21 mirror)
- buttons: `Shot,Bomb,Rapid Shot,Weapon Change,Start,Coin,Test,Service,Save State`, default `A,B,X,Y,Start,R,L,Select`

## README

Sections: title and one-line description, to-do list, about, change notes (song table + other
changes table), patching (required inputs, web patcher link
`https://iamthechuckster.github.io/Ibara_Kuro_Show_Time/`, MiSTer, Python), result checksums,
for developers, testing (MAME 0.289, MiSTer CV1k core), credits (IAmTheChuckster: project and
testing; Claude: reverse engineering and patcher code), disclaimer (unofficial, not affiliated
with CAVE, no ROM data distributed).
