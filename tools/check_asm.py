#!/usr/bin/env python3
"""Check that the routines in showtime_patch.py match the sources in asm/.

    python tools/check_asm.py
"""
import importlib.util
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from sh3asm import assemble   # noqa: E402

spec = importlib.util.spec_from_file_location("sp", here.parent / "showtime_patch.py")
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
ok = True
for name, at, code in (("menu_line.s", sp.TRAMPOLINE, sp.TRAMPOLINE_CODE),
                       ("bomb_spawn.s", sp.SPAWN_CODE_AT, sp.SPAWN_CODE),
                       ("bomb_use.s", sp.BOMB_CODE_AT, sp.BOMB_CODE),
                       ("p2_toggle.s", sp.INPUT_AT, sp.INPUT_CODE),
                       ("select_mark.s", sp.MARK_AT, sp.MARK_CODE),
                       ("bomb_keep.s", sp.KEEP_AT, sp.KEEP_CODE),
                       ("new_game.s", sp.NEWGAME_AT, sp.NEWGAME_CODE),
                       ("hadou_keep.s", sp.HADOU_AT, sp.HADOU_CODE),
                       ("test_mode.s", sp.TESTM_AT, sp.TESTM_CODE)):
    built = assemble(at, (here.parent / "asm" / name).read_text())
    same = built == code
    ok &= same
    print(f"{name:14s} {'ok' if same else 'DIFFERENT'}")
sys.exit(0 if ok else 1)
