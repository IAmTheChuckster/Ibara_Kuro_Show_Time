---
name: "cv1000-learn-game"
description: "Set up the CV1000 MAME 0.289 test package with an attached ROM set, then play and study the game headlessly to learn its mechanics before any patching."
---

# Learn a CV1000 game in MAME 0.289

Use when the user attaches `cv1k_mame0289_testenv.tar.gz` (or a newer cv1k test package) plus a MAME ROM set (`<set>.zip` or loose files) and asks to play / learn / study the game. The goal is a clear, verified picture of how the game works, written down before any ROM changes. Never modify the ROMs in this phase.

## Standing rules
- Always use MAME 0.289 (the binary in the package). Do not fall back to another version without asking.
- No ROM data goes into any git repo or public artifact.
- The user often interrupts: when interrupted, stop and wait.
- Keep messages short; send screenshots (a strip of frames) rather than long descriptions.

## 1. Set up (5 minutes)
1. Unpack: `mkdir -p ~/cv1k && tar xzf <package> -C ~/cv1k`; `cd ~/cv1k/cv1k_testenv`.
2. Check the binary runs: `bin/cv1k -version`. If libraries are missing, install `$(cat bin/apt_packages.txt)`; if it still fails, rebuild with `scripts/build_mame.sh mame0289` (about 25 min on 2 cores) and tell the user.
3. ROMs: put the zip as `roms/<set>.zip` (no unpacking needed) or loose files in `roms/<set>/`. If the set is a clone, the parent zip is needed too; ask for it if missing. Find the set name with `bin/cv1k -listxml <set>` or `bin/cv1k -listfull | grep -i <title>`.
4. `export GAME=<set> ROMPATH=$PWD/roms`.
5. Boot twice: `scripts/boot_test.sh 1500` (the first boot initialises EEPROM/NAND and shows "wait a moment"; the second is the normal boot). Send the snapshot strip from `work/snap/boot/`. A wrong-checksum warning for the u4 is only expected on patched ROMs; for an unpatched set it means a bad dump.
6. Note the board type: sets using the `cv1k_d` machine are CV1000-D (4 MB u4, 16 MB RAM at 0x0C000000-0x0CFFFFFF); others are CV1000-B (2 MB u4, 8 MB RAM at 0x0C000000-0x0C7FFFFF).

## 2. Get into a game
- Inputs for `BT_SCHED` files (`frame tokens`, held until the next line, `-` = nothing): `U D L R` stick, `A B C Q` buttons 1-4, `K` coin 1, `V` service coin, `S` 1P start, `T` 2P start, `X` service DIP.
- Typical: `900 K` / `906 -` / `1000 S` / `1006 -`, then more `S` or `A` presses to pass menus and character select. Take snapshots every 100 frames (`BT_SNAP`) to see each screen and adjust timings.
- Use `lua/harness.lua` as the template for longer work: copy it to `lua/<set>_harness.lua`, replace the Pink Sweets addresses, and use its boot mode (schedule from power-on, save a state at a chosen frame) and run mode (load the state, play a schedule, dump memory every frame, snapshots, breakpoints). Save states are per MAME version.
- Save a state at the start of stage 1 for each character/ship, so later tests start in seconds.

## 3. Learn the mechanics
Work in short runs (a few thousand frames) and check each finding in memory or the disassembly, not just by eye.
1. **Attract mode and How to Play:** snapshot the demo and instruction screens; they show the intended controls and systems. Translate any Japanese text.
2. **Controls:** for each button alone and in combinations (hold, tap, rapid), record what happens: shot types, bombs/specials, speed changes, option formations. Measure fire rates and speeds in frames/pixels from per-frame memory dumps.
3. **Find the player data:** dump work RAM every frame while moving and shooting; search for the X/Y position (it changes with the stick), lives, bombs, score, power level, gauges. The player structure is usually one block; note its address and field offsets.
4. **Scoring and systems:** what gives points (enemies, items, grazing, chains, bonuses), extends, rank/difficulty (find the rank variable and what raises it), continues, stage timers.
5. **Code:** disassemble the main program (it runs from RAM after the boot copy: dump RAM after boot, or read the u4) with `sh-elf-objdump -D -b binary -m sh -EB --adjust-vma=<base>` and use watchpoints (`scripts/debug_trace.sh 'wpset <addr>,<len>,w,1,{logerror "pc=%08x\n",pc;go}'`) to find the routine that writes each value.
6. **Sound:** the YMZ770 is at 0x10400000 (register select) / 0x10400001 (data). Logging writes shows sequence (music) starts on 0x80+ registers and channel starts on 0x40-0x5F.
7. **Auto-play:** to see later stages, build a schedule that moves and fires continuously and, once the lives address is known, hold the death/invulnerability counter or lives in the harness. Snapshot every 1000 frames and save a state at each new stage.
8. **DIP/service menu:** boot with `X` held to see test mode; record difficulty, lives, extend and other settings and their RAM variables.

## 4. Report
Write the findings to the project as a doc (for example `claude/<set>-mechanics.md`): set name and board type, controls table, player structure, key RAM variables, scoring and rank rules, stage list with BGM sequence numbers, useful code addresses, save states made, and open questions. Send the user a short summary with the most useful screenshots, then ask what they want to change before any patching starts.