# Ibara Kuro Show Time

## To do
1. Replace Warning Screen
2. lower the countdown volume, if the chime and laughter are separate then remove the chime.

A gameplay patch for Ibara Kuro Black Label (2006/02/06. MASTER VER.)<br> 
This repository holds only source, tools and notes. **No ROM data is included**; you patch your own dump.

## About this project
Why did I make this? Because it's fun and for my own personal research to see the capabilities of Claude.

## What it changes

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

## Testing
This patch was tested with MAME 0.289 and [CV1k core for the MiSTer FPGA by Raki](https://www.patreon.com/c/ikamusume/posts)<br>
It may even work on a PCB but do so on your own risk.

## Credits

- [IAmTheChuckster](https://github.com/IAmTheChuckster)  project, testing
- [Claude](https://claude.ai) (Anthropic)  reverse engineering and patcher code
- Tested on the CV1k core for the MiSTer FPGA by [Raki](https://www.patreon.com/c/ikamusume/posts)

## Disclaimer

This repository contains a fan-made patch for research and technical analysis. The repository does not intentionally distribute the original game ROM, executable, or game assets. Users must obtain their own copy of the original game. This project is unofficial and is not affiliated with, endorsed by, or authorized by CAVE. All rights to the original game and its associated intellectual property remain with their respective rights holders. No license to third-party copyrighted material is granted by this repository.
