# 2048 Terminal Game

A feature-rich terminal implementation of the classic 2048 game built with Python curses.

## Features

- **Classic 2048 gameplay** — Merge tiles to reach 2048
- **Configurable board size** — Play 4×4, 5×5, or any custom size
- **Undo support** — Revert up to 20 moves
- **Hint system** — Get intelligent move suggestions
- **Pause functionality** — Take breaks anytime
- **Persistent high scores** — Best scores saved to `~/.2048_best_score`
- **Save/Load games** — Resume interrupted sessions (`s` to save, `l` to load)
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
# Default 4x4 board
python3 game2048.py

# Custom board size
python3 game2048.py --size 5
```

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

### Undo System
Press `u` to undo moves (up to 20 steps back). Useful for recovering from mistakes.

### Hint System
Press `h` to see the suggested move direction. The hint algorithm evaluates each direction by maximizing empty cells and total tile value — a simple but effective heuristic.

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

## License

MIT
