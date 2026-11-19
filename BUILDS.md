# Web patcher builds

Each change to `index.html` is a new build. When you make one, bump `const BUILD` in
`index.html` (it shows in the status column as "Matches Build N") and add a row here.

| Build | Date | Commit | Changes |
|---|---|---|---|
| 1 | 2026-10-21 | `eb2faf7` | First version, added with the Python patcher |
| 2 | 2026-10-21 | `0c9c1f5` | Outputs named `ibarashow_u4` / `ibarashow_u23`; romset download |
| 3 | 2026-10-22 | `45ddec0` | Warning screen, NOT FOR SALE, bomb counts, Dyne select, quieter beep |
| 4 | 2026-10-22 | `5bcad38` | MiSTer MRA and download button |
| 5 | 2026-10-22 | `c371564` | MRA renamed to Ibara Kuro Show Time.mra |
| 6 | 2026-10-22 | `4f5f30b` | Start on ship select (MiSTer), name entry after Dyne, INFINITE hadou gun, beep 40% |
| 7 | 2026-10-29 | `f1e9b8a` | Dyne mode control fix after test mode / demo; boot line 2026/10/29 |
| 8 | 2026-11-20 | `ffcd4f8` | Removed "Download patched files"; romset and MRA on one row |
| 9 | 2026-11-20 | `3edbd4b` | Comments updated for the `patch.py` rename |
| 10 | 2026-11-20 | `0fb47dd` + this commit | Removed u4/u23 download buttons; build number shown in status |
