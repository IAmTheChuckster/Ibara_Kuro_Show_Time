# Ibara Kuro Show Time

## To do
1. Replace Warning Screen
2. lower the countdown volume by half, if the chime and laughter are separate then raise the laughter volume.
3. Select character by pressing the start button
4. Add infinite bomba in the Service menu
5. upload skill
6. add mra to patcher

A gameplay patch for Ibara Kuro Black Label (2006/02/06. MASTER VER.)<br> 
This repository holds only source, tools and notes. **No ROM data is included**; you patch your own dump.

## About this project
Why did I make this? Because it's fun and for my own personal research to see the capabilities of Claude.

## Change notes
It changes the songs so it plays Ibara loop one instead of loop two tracks from Ibara. Why would anyone want to do this? Because the music from loop one is better.

| Black Label song   | Plays instead | 
|--------------------|---------------|
| Bonds of Steel     | Show Time     | 
| Air Pollution      | Sky High      | 
| The Family's Work  | Robot No28    | 

## Patching the game
The following source files are required
| File Name   |   CRC    |
|-------------|----------|
| ibarablk_u4 | ee1f1f77 |
| u23         | a436bb22 |

### In your browser
Open the **[Show Time Patcher](https://iamthechuckster.github.io/Ibara_Kuro_Show_Time/)** (`index.html`) and drop in your `ibarablk.zip`. It checks the file names and CRCs, builds the patched files automatically, and lets you download just the patched files or a complete `ibarashow.zip` romset. Everything runs in your browser; nothing is uploaded.

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
| ibarashow_u4  | 07243591 |
| ibarashow_u23 | 69403f24 |

`ibarablk_u2` and `u24` are unchanged (copied into the complete romset).

## Testing
This patch was tested with MAME 0.289 and [CV1k core for the MiSTer FPGA by Raki](https://www.patreon.com/c/ikamusume/posts)<br>
It may even work on a PCB but do so on your own risk.

## Credits

- [IAmTheChuckster](https://github.com/IAmTheChuckster)  project, testing
- [Claude](https://claude.ai) (Anthropic)  reverse engineering and patcher code
- Tested on the CV1k core for the MiSTer FPGA by [Raki](https://www.patreon.com/c/ikamusume/posts)

## Disclaimer

This repository contains a fan-made patch for research and technical analysis. The repository does not intentionally distribute the original game ROM, executable, or game assets. Users must obtain their own copy of the original game. This project is unofficial and is not affiliated with, endorsed by, or authorized by CAVE. All rights to the original game and its associated intellectual property remain with their respective rights holders. No license to third-party copyrighted material is granted by this repository.
