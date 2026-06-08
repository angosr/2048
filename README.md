# 2048 Terminal Game

A feature-rich terminal implementation of the classic 2048 game built with Python curses.

## Features

- **Classic 2048 gameplay** — Merge tiles to reach 2048
- **Configurable board size** — Play 4×4, 5×5, or any custom size
- **Difficulty levels** — Easy / Normal / Hard with different spawn probabilities
- **Elapsed timer** — Real-time game duration display (mm:ss / hh:mm:ss)
- **Auto-save & recovery** — Game auto-saves on quit; resume with `--recover`
- **Undo support** — Revert up to 20 moves
- **Smart hint system** — AI suggestions using monotonicity, smoothness, and corner strategy
- **Enhanced pause** — Toggle pause anytime; timer pauses with the game
- **Color themes** — Choose from classic, monochrome, or warm palettes
- **Persistent high scores** — Best scores saved to `~/.2048_best_score`
- **Save/Load games** — Manual save (`s`) and load (`l`) for interrupted sessions
- **Visual feedback** — Color-coded tiles with merge flash animations
- **Statistics tracking** — Score, moves, tile counts, averages
- **Input throttling** — Smooth controls with 60ms debounce
- **Multiple control schemes** — Arrow keys, WASD, or Vim keys (HJKL)

## Requirements

- Python 3.7+
- curses (included with Python on Unix/macOS systems)

## Installation

```bash
git clone git@github.com:angosr/2048.git
cd 2048
chmod +x game2048.py
```

## Usage

```bash
# Default 4x4 board, normal difficulty
python3 game2048.py

# Custom board size
python3 game2048.py --size 5

# Easy difficulty with warm theme
python3 game2048.py --difficulty easy --theme warm

# Hard difficulty, monochrome theme
python3 game2048.py --difficulty hard --theme monochrome

# Recover auto-saved game
python3 game2048.py --recover
```

### Command-line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--size N` | Board size (N×N) | 4 |
| `--difficulty` | `easy`, `normal`, or `hard` | normal |
| `--theme` | `classic`, `monochrome`, or `warm` | classic |
| `--recover` | Resume from auto-saved game | off |

### Difficulty Presets

| Level | 2-tile chance | 4-tile chance |
|-------|--------------|---------------|
| Easy  | 80%          | 20%           |
| Normal| 90%          | 10%           |
| Hard  | 95%          | 5%            |

## Controls

| Action                  | Keys                           |
|-------------------------|--------------------------------|
| Move tiles              | Arrow keys / WASD / HJKL       |
| Undo last move          | `u` or `U`                    |
| Get hint                | `h` or `?`                    |
| Pause / resume          | `p` or `P`                    |
| Save game               | `s` or `S`                    |
| Load saved game         | `l` or `L`                    |
| New game                | `r` or `R`                    |
| Quit                    | `q` or `Q`                    |
| Continue after winning  | `c` or `C`                    |

## Game Features

### Timer
The elapsed time is shown in the stats bar. The timer pauses automatically when the game is paused.

### Difficulty Levels
- **Easy** — Higher chance of 4-tiles spawning (20%), making merges easier
- **Normal** — Standard 2048 spawn rates (10% for 4-tiles)
- **Hard** — Lower chance of 4-tiles (5%), requiring more strategic play

### Auto-save & Recovery
The game automatically saves your progress when you quit. Use `--recover` on the next launch to resume where you left off. Manual save/load (`s`/`l`) is also available.

### Smart Hint System
Press `h` to get AI-powered move suggestions. The hint algorithm evaluates each direction using:
- **Monotonicity** — Prefers ordered tile arrangements
- **Smoothness** — Minimizes value differences between adjacent tiles
- **Corner strategy** — Rewards keeping the highest tile in a corner
- **Merge potential** — Counts available merges

### Color Themes
- **Classic** — Vibrant multi-color palette (default)
- **Monochrome** — Single-hue gradient for minimalist look
- **Warm** — Earth-tone palette with reds and oranges

### Enhanced Pause
Press `p` to pause/resume. While paused, the grid is hidden and the timer stops.

### Undo System
Press `u` to undo moves (up to 20 steps back). Useful for recovering from mistakes.

### Save/Load
- Press `s` to save the current game state to `~/.2048_save.json`
- Press `l` to restore the most recent save
- The save includes the grid, score, moves, and all game state

### Statistics
The top bar displays real-time stats:
- **Score** — Current game score
- **Best** — All-time high score (persisted)
- **Max** — Highest tile value on the board
- **Avg** — Average value of non-zero tiles
- **Tiles** — Number of occupied cells
- **Mv** — Total moves made
- **Time** — Elapsed game time

## License

MIT
