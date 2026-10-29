# Ibara Kuro Show Time
A gameplay patch for Ibara Kuro Black Label (2006/02/06. MASTER VER.)<br> 
This repository holds only source, tools and notes. **No ROM data is included**; you patch your own dump.

## To do
1. lower the beep to 40% of original
2. raise the laughter by 50%
3. make an option to keep the original soundtrack
4. add another option and call it something like Kuro+ but make it so focus shot sucks in medals for MOAR SCORE!!!!!!!
5. Update MRA files to include button names
   
## About this project
Why did I make this? Because it's fun and for my own personal research to see the capabilities of Claude.<br> 
While Claude was used I put effort in making sure there are balanced gameplay.<br> 
I did all the testing and planning.

## Change Notes
It changes the songs so it plays Ibara loop one instead of loop two tracks from Ibara. Why would anyone want to do this? Because the music from loop one is better.

| Black Label song   | Plays instead | 
|--------------------|---------------|
| Bonds of Steel     | Show Time     | 
| Air Pollution      | Sky High      | 
| The Family's Work  | Robot No28    | 

Other changes:

| Where | Change |
|---|---|
| Warning screen | New text: *This project is unofficial and is not affiliated with, endorsed by, or authorized by CAVE. All rights to the original game and its associated intellectual property remain with their respective rights holders. Have fun!!!* Bottom line: `2026/10/29 SHOW TIME` |
| Title screen | `SALE BY AMI` → `NOT FOR SALE` |
| Test mode → DIP SWITCH SETTING | New **bomb counts** line under player counts: `1` (default), `2`, `3`, `4`, `FULL`, `INFINITE`. Sets the full bombs you have at the start and after each respawn (you never get fewer than the normal game gives). `FULL` = 4 bombs and all 40 small bombs; `INFINITE` = 4 bombs and 40 small bombs that are never used up, by a normal bomb or by the hadou gun (bomb button held). Saved with the other settings. |
| Ship select | **Start** switches between Bond (Player 1) and Dyne (Player 2); press again to switch back. Your Player 1 controls fly whichever you pick, and also enter your name after the game. The empty panel no longer shows credit text. Only in a one-player game; a second player can still join normally. Test mode always uses the normal controls, and Start on the title or attract demo always starts a normal game. |
| Sound | The countdown beep (coin countdown, continue, name entry) is at 40% volume. The laughs are separate sounds and are unchanged. |

## Patching the game
The following source files are required
| File Name   |   CRC    |
|-------------|----------|
| ibarablk_u4 | ee1f1f77 |
| u23         | a436bb22 |

### In your browser
Open the **[Show Time Patcher](https://iamthechuckster.github.io/Ibara_Kuro_Show_Time/)** (`index.html`) and drop in your `ibarablk.zip`. It checks the file names and CRCs, builds the patched files automatically, and lets you download just the patched files or a complete `ibarashow.zip` romset. Everything runs in your browser; nothing is uploaded.

### MiSTer
`Ibara Kuro Show Time.mra` (also a download button on the web patcher) is for the CV1k core. It expects the complete romset as `ibarashow.zip` (`ibarashow_u4` `59721266`, `ibarashow_u23` `69403f24`, `ibarablk_u2` `5e46be44`, `u24` `d11ab6b6`).

### With Python
Requires Python 3.8+ (standard library only).
```sh
python showtime_patch.py ibarablk.zip                    # patched files go to ./output
python showtime_patch.py ibarablk.zip --zip ibarashow.zip # also a complete romset
python showtime_patch.py --help           # more options
```

### Result
| File Name   |   CRC    |
|-------------|----------|
| ibarashow_u4  | 59721266 |
| ibarashow_u23 | 69403f24 |

`ibarablk_u2` and `u24` are unchanged (copied into the complete romset).

### For developers
The new code is in `asm/` (SH-3 assembly) and is checked against the bytes in `showtime_patch.py` with `python tools/check_asm.py`. `tools/gen_web_extras.py` regenerates the edit table used by `index.html`, so the web patcher and the Python script always produce the same files.

## Testing
This patch was tested with MAME 0.289 and [CV1k core for the MiSTer FPGA by Raki](https://www.patreon.com/c/ikamusume/posts)<br>
It may even work on a PCB but do so on your own risk.

## Credits

- [IAmTheChuckster](https://github.com/IAmTheChuckster)  project, testing
- [Claude](https://claude.ai) (Anthropic)  reverse engineering and patcher code
- Tested on the [CV1k core for the MiSTer FPGA by Raki](https://www.patreon.com/c/ikamusume/posts)

## Disclaimer

This repository contains a fan-made patch for research and technical analysis. The repository does not intentionally distribute the original game ROM, executable, or game assets. Users must obtain their own copy of the original game. This project is unofficial and is not affiliated with, endorsed by, or authorized by CAVE. All rights to the original game and its associated intellectual property remain with their respective rights holders. No license to third-party copyrighted material is granted by this repository.
