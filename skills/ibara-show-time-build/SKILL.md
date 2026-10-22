---
name: ibara-show-time-build
description: Rebuild the Ibara Kuro "Show Time" ROM patch from scratch (Python patcher, browser patcher, MiSTer MRA, SH-3 routines) from an original ibarablk dump, and test it in MAME 0.289.
---

# Ibara Kuro Show Time: build from scratch

Recreates everything in https://github.com/IAmTheChuckster/Ibara_Kuro_Show_Time from the user's
own Ibara Kuro Black Label dump. **Never put ROM data in the repo, the web page or any output that
is shared**; only new code, new text and changed-byte tables.

## 0. Inputs and expected results
| File | CRC32 | Notes |
|---|---|---|
| ibarablk_u4 | ee1f1f77 | program (patched) |
| u23 | a436bb22 | sound (patched) |
| ibarablk_u2 | 5e46be44 | NAND, copied unchanged |
| u24 | d11ab6b6 | copied unchanged |

Outputs: `ibarashow_u4` **531d55da** (sha1 796b4540f1cd0be2dbc5c3238b2a74ba042e8b8d),
`ibarashow_u23` **69403f24** (sha1 51f6536b0845fc26f266761ae344992fb38ffee8). Complete romset zip:
`ibarashow.zip` = those two + ibarablk_u2 + u24. If you reproduce the features exactly, the CRCs
must match; check with the published values before shipping.

## 1. Set up
1. Clone the repo (or start an empty one). Ask the user for `ibarablk.zip`; never commit it.
2. MAME test env: use the `cv1000-learn-game` skill (MAME 0.289 cv1k build, headless, `-nodrc`).
   Put the dev build in `roms_dev/ibarablk/` (MAME set name `ibarablk`, file names unchanged).
   Harness `lua/ibara.lua` with env vars: IB_FRAMES, IB_SCHED (file of `frame tokens`; tokens
   U D L R A B C Q = P1, K coin, S/T P1/P2 start, `-` release), IB_SNAP, IB_DUMP (8 MB RAM),
   IB_POKE `from:to:addr:val`, IB_MEM `frame:addr:len`, IB_OUT. Debugger traces: run MAME with
   `-debug -debugger none -log` and a Lua script issuing `wpset`/`bpset` with `logerror`.

## 2. Program format
- Files are 16-bit word-swapped. ibarablk_u4: LZSS-packed program at ROM 0x51000, unpacked to RAM
  0x0C051000 (header: size, item count, data offset; flag bytes MSB first; match word =
  dist<<5 | (len-3), dist ≤ 2047, len 3–34). Unpacked program sha1 531fc52e0d84866bca8509f36a9c9e6319667bea.
- Repack with a deterministic optimal-parse LZSS (hash chains + backward cost DP: literal 9 bits,
  match 17), packed data must end before 0xFB4C0. Python and JS implementations must be identical
  so both patchers give byte-identical files. Always verify by unpacking again.
- Disassemble the unpacked program with SH-3 objdump (`sh-elf-objdump -b binary -m sh3 -EB
  --adjust-vma=0x0C051000 -D`).

## 3. Features and where they live
| Feature | Edit |
|---|---|
| Music | Bonds of Steel→Show Time, Air Pollution→Sky High, The Family's Work→Robot No28. u23 sequence table at 0x400 + 4·id (intro/loop ids: Show Time 0F/10, Sky High 11/12, Robot No28 17/18, Bonds of Steel 1B/1C, Family's Work 1D/1E, Air Pollution 1F/20); copy play-time entries in tables 0x0C0C3A58 and 0x0C0C3E58; rename the slot in the title list 0x0C2069B4–0x0C206A88 (`$Name\0`). |
| Boot line | `2026/10/22 SHOW TIME` at 0x0C0C4E08 and 0x0C0C4F88 (30 bytes, 4 leading spaces); nop the clock-date calls 0x0C06BC82/0x0C06BC8E (`490b`→`0009`). |
| Warning screen | Japan block 0x0C0C4C68 (12 × 32-byte lines), export 0x0C0C4E28 (11 lines; its 12th slot is the boot line). Uppercase font only. |
| Title | `SALE BY AMI` → `NOT FOR SALE`: text placed in spare warning line 0x0C0C4DC8, literal 0x0C06A688 re-pointed. |
| DIP "bomb counts" | 1/2/3/4/FULL/INFINITE (values 0–5, default 0) on the hidden menu index 12 (variable 0x0C23DEA4, already saved); menu tables near 0x0C1731FC/0x0C173248/0x0C17325C, strings at 0x0C173800, draw routine `asm/menu_line.s` @0x0C05B700. |
| Bombs | Player block 0x0C29D1D8 + p·0x2A0: +0x25D full bombs (max 4), +0x25E small bombs (max 40; at 40 the game spends them first). Spawn hook 0x0C06D216 → stub 0x0C06D3B4 → `bomb_spawn.s` @0x0C05B680 (full = max(normal, setting+1); FULL/INFINITE also 40 small). Bomb store 0x0C0736B6 → stub 0x0C073724 → `bomb_use.s` @0x0C05B6C0. Small-bomb checks 0x0C0736A8 and 0x0C0737D0 → stub 0x0C0737B4 → `bomb_keep.s` @0x0C05B620 (report 0 when INFINITE). The hadou gun (bomb held) has its own store at 0x0C0737DA → stub 0x0C0737F4 → `hadou_keep.s` @0x0C05B660. |
| Ship select Start = Bond/Dyne | Control reader 0x0C060E54 (bra) → stub 0x0C060DD4 → `p2_toggle.s` @0x0C05B500, returns to 0x0C060E58 with r6 = start/coin byte, r4/r1 = P1/P2 port. State 0x0C05B4F0: +0 Dyne flag, +1 Start held, +2 select-active counter (set to 3 each frame by hook 0x0C0B8390 → stub 0x0C0B8384 → `select_mark.s` @0x0C05B600). Toggle when choosing mask 0x0C239497 == flag+1 and P1 Start newly pressed: swap the two 0x2A0-byte player blocks, fix pilot bit (+7 bit 3), mask ^= 3, flag ^= 1; hide that Start press. In Dyne mode swap P1/P2 ports (A4000126/A4000134) and Start bits 0x10/0x20, but only while mode byte 0x0C2A6D64 == 6 (play, continue, name entry) or select active. Flag cleared at new-game init 0x0C06A7B4 → stub 0x0C06AE44 → `new_game.s` @0x0C05B640. Remove the empty-panel credit text: jsr→nop at 0x0C06DA5C/68/82/9C. |
| Beep | Countdown beep = effect 0x5C; default volume byte 0x0C206824+0x5C: 0xFC → 0x65 (40%, level is linear). |

Pitfalls learned: 0x0C2289ED is not a scene variable (temporary pointer byte) – it broke the
toggle on MiSTer. Player blocks are non-zero during attract, so they can't mean "in a game". The
countdown 0x0C3C8474 stays non-zero after an early name entry. Always find the real state byte by
diffing RAM dumps across title / attract / game / name entry.

## 4. Hooking rules (SH-3)
- New code goes in the zero area 0x0C05B4F0–0x0C05B733 (check it is zero in the original).
- 12-byte nop padding between functions holds a stub: `d001 402b 0009 0009 .long target`
  (jumps via r0) or `d101 412b ...` (via r1) when r0 is live. Reach it with `bsr` only if the host
  function saved PR; in leaf functions use `bra` and `jmp` back to a fixed address.
- The replaced instruction(s) are redone in the routine or kept in the bsr delay slot.
- Assemble `asm/*.s` with `tools/sh3asm.py`; `tools/check_asm.py` must report every file `ok`
  against the bytes in `showtime_patch.py`.

## 5. Deliverables
1. `showtime_patch.py` (stdlib only): checks input CRC/SHA-1, applies music, boot text and
   `apply_extras()` (all table edits above), repacks, verifies against DEFAULT_OUTPUTS, writes
   `ibarashow_u4`/`ibarashow_u23`; `--zip ibarashow.zip` adds u2/u24 unchanged.
2. `index.html` browser patcher: a JS port of the same steps; the fixed edits come from
   `python tools/gen_web_extras.py ibarablk.zip` (changed bytes only, never original data).
   Verify with Node that the JS result equals the Python result. Buttons: patched files zip,
   complete romset `ibarashow.zip`, raw files, and `Download Ibara Kuro Show Time.mra`.
3. `Ibara Kuro Show Time.mra` for the ikacore_CV1k MiSTer core: zip `ibarashow.zip`; rom 1
   ibarablk_u2 @0x34400000; rom 2 @0x3C800000 ibarashow_u23 + 0x400000 zeros + u24 + 0x400000
   zeros; nvram index 3 size 135680; rom 0 ibarashow_u4 listed twice; all with CRCs.
4. README with the change table, input/output CRCs, and the disclaimer.

## 6. Test checklist (MAME, then ask the user to test on MiSTer)
- Warning screen, boot line, NOT FOR SALE.
- DIP menu: cycle, save (A on "save", Start, confirm), reboot keeps it.
- Bombs per setting; INFINITE: tap bomb and hold for the hadou gun – counts never drop
  (compare a normal setting, which loses one).
- Ship select: Start toggles Bond/Dyne repeatedly, also with coins and free play; game starts as
  the chosen pilot; 2-player start unaffected.
- Dyne game → game over → name entry works with the P1 controls → next game starts as Bond.
- Beep level with `-wavwrite` (peak ~40% of original).
- Final CRCs equal the table in section 0; Python == web output; MRA CRCs updated.
