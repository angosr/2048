#!/usr/bin/env python3
"""Enhanced CLI 2048 Game with Curses TUI."""
import argparse
import curses
import os
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

_COLOR_PAIR_CACHE = {}
_PAIR_COUNTER = 0


def _ensure_pair(fg, bg):
    """Safely allocate a curses color pair with caching to avoid init_pair count limits."""
    global _PAIR_COUNTER
    k = (fg, bg)
    if k in _COLOR_PAIR_CACHE:
        return _COLOR_PAIR_CACHE[k]
    _PAIR_COUNTER += 1
    p = _PAIR_COUNTER
    curses.init_pair(p, fg, bg)
    _COLOR_PAIR_CACHE[k] = p
    return p


KEY_TO_DIR = {
    ord('k'): 'up', ord('K'): 'up',
    ord('j'): 'down', ord('J'): 'down',
    ord('h'): 'left', ord('H'): 'left',
    ord('l'): 'right', ord('L'): 'right',
    curses.KEY_UP: 'up', curses.KEY_DOWN: 'down',
    curses.KEY_LEFT: 'left', curses.KEY_RIGHT: 'right',
}

_TILE_PALETTE = {
    0:    (curses.COLOR_BLACK, curses.COLOR_WHITE),
    2:    (curses.COLOR_BLACK, curses.COLOR_BLUE),
    4:    (curses.COLOR_BLACK, curses.COLOR_MAGENTA),
    8:    (curses.COLOR_WHITE, curses.COLOR_RED),
    16:   (curses.COLOR_WHITE, curses.COLOR_RED),
    32:   (curses.COLOR_WHITE, curses.COLOR_RED),
    64:   (curses.COLOR_WHITE, curses.COLOR_RED),
    128:  (curses.COLOR_BLACK, curses.COLOR_YELLOW),
    256:  (curses.COLOR_BLACK, curses.COLOR_YELLOW),
    512:  (curses.COLOR_BLACK, curses.COLOR_YELLOW),
    1024: (curses.COLOR_BLACK, curses.COLOR_CYAN),
    2048: (curses.COLOR_BLACK, curses.COLOR_GREEN),
}


class GameEngine:
    """Core 2048 game logic with undo history and stats."""

    def __init__(self, size=4):
        self.size = size
        # Undo history: up to 20 snapshots
        self._history = []
        # Tiles that just merged (for flash animation)
        self._flash_map = set()
        self.grid = [[0] * size for _ in range(size)]
        self.score = 0
        self.best_score = self._load_best_score()
        self.total_moves = 0
        self.won = False
        self.continue_after_win = False
        self.over = False
        self._last_flash_time = 0
        self.add_random_tile()
        self.add_random_tile()

    @staticmethod
    def _load_best_score():
        p = Path.home() / '.2048_best_score'
        if p.exists():
            try:
                return int(p.read_text().strip())
            except Exception:
                pass
        return 0

    def _save_best_score(self):
        if self.score > self.best_score:
            self.best_score = self.score
            try:
                (Path.home() / '.2048_best_score').write_text(str(self.best_score))
            except Exception:
                pass

    def snapshot(self):
        """Push current grid onto undo stack."""
        self._history.append(deepcopy(self.grid))
        if len(self._history) > 20:
            self._history.pop(0)

    def undo(self):
        """Restore previous board state. Returns True if successful."""
        if not self._history:
            return False
        self.grid = self._history.pop()
        self._flash_map.clear()
        return True

    @property
    def can_undo(self):
        return bool(self._history)

    def move(self, direction):
        """Attempt a move. Returns True if the board changed."""
        if self.over or (self.won and not self.continue_after_win):
            return False
        self.snapshot()
        old_grid = [row[:] for row in self.grid]
        total_pts = 0
        rows = list(range(self.size))
        cols = list(range(self.size))
        if direction == 'down':
            rows.reverse()
        elif direction == 'right':
            cols.reverse()
        if direction in ('left', 'right'):
            for r in rows:
                line = [self.grid[r][c] for c in cols]
                nl, pts = self._slide(line)
                total_pts += pts
                for i, c in enumerate(cols):
                    self.grid[r][c] = nl[i]
        else:
            for c in cols:
                col = [self.grid[r][c] for r in rows]
                nc, pts = self._slide(col)
                total_pts += pts
                for i, r in enumerate(rows):
                    self.grid[r][c] = nc[i]
        changed = any(self.grid[r][c] != old_grid[r][c]
                      for r in range(self.size) for c in range(self.size))
        if changed:
            self.score += total_pts
            self.total_moves += 1
            self._last_flash_time = time.monotonic()
            self.add_random_tile()
            self._clear_old_flashes()
            self._save_best_score()
            if not self.won and any(self.grid[r][c] == 2048
                                    for r in range(self.size)
                                    for c in range(self.size)):
                self.won = True
            if self.is_game_over():
                self.over = True
        return changed

    @staticmethod
    def _slide(line):
        nz = [x for x in line if x != 0]
        merged = []
        points = 0
        i = 0
        while i < len(nz):
            if i + 1 < len(nz) and nz[i] == nz[i + 1]:
                v = nz[i] * 2
                merged.append(v)
                points += v
                i += 2
            else:
                merged.append(nz[i])
                i += 1
        merged.extend([0] * (len(line) - len(merged)))
        return merged, points

    def add_random_tile(self):
        empty = [(r, c) for r in range(self.size) for c in range(self.size)
                 if self.grid[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def get_max_tile(self):
        return max(max(row) for row in self.grid)

    def tile_count(self):
        return sum(1 for r in range(self.size) for c in range(self.size)
                   if self.grid[r][c] != 0)

    def is_game_over(self):
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == 0:
                    return False
                v = self.grid[r][c]
                if c < self.size - 1 and v == self.grid[r][c + 1]:
                    return False
                if r < self.size - 1 and v == self.grid[r + 1][c]:
                    return False
        return True

    def find_hint(self):
        """Return the direction that leaves the most open space after sliding."""
        best_dir = None
        best_sc = -1
        for d in ('up', 'down', 'left', 'right'):
            g2 = [row[:] for row in self.grid]
            rows, cols = list(range(self.size)), list(range(self.size))
            if d == 'down':
                rows.reverse()
            elif d == 'right':
                cols.reverse()
            if d in ('left', 'right'):
                for r in rows:
                    line = [self.grid[r][c] for c in cols]
                    nl, _ = self._slide(line)
                    for i, c in enumerate(cols):
                        self.grid[r][c] = nl[i]
            else:
                for c in cols:
                    col = [self.grid[r][c] for r in rows]
                    nc, _ = self._slide(col)
                    for i, r in enumerate(rows):
                        self.grid[r][c] = nc[i]
            empties = sum(1 for r in range(self.size) for c in range(self.size)
                          if self.grid[r][c] == 0)
            sc = empties * 10 + sum(sum(row) for row in self.grid)
            self.grid = g2
            if sc > best_sc:
                best_sc = sc
                best_dir = d
        return best_dir

    def reset(self):
        self.grid = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self._history.clear()
        self._flash_map.clear()
        self.total_moves = 0
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.add_random_tile()
        self.add_random_tile()

    def _clear_old_flashes(self):
        cutoff = self._last_flash_time
        self._flash_map = {p for p in self._flash_map
                           if time.monotonic() - cutoff < 0.15}


def render_board(stdscr, game):
    """Unified renderer — replaces 3 dead duplicate renderers in original."""
    curses.start_color()
    curses.use_default_colors()
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    MAX_W = 200

    # --- Tiny terminal fallback ---
    if h < 12 or w < 30:
        stdscr.nodelay(False)
        for i, row in enumerate(game.grid):
            try:
                txt = ' | '.join(str(v) if v else '.' for v in row)
                stdscr.addstr(i + 2, 1, txt[:MAX_W])
            except curses.error:
                pass
        ctrl = 'Arrow Keys:move  R:new  Q:quit  u:undo  h:hint  p:pause'
        try:
            stdscr.addstr(h - 2, 0, ctrl[:MAX_W], curses.A_DIM)
        except curses.error:
            pass
        stdscr.refresh()
        return

    sz = game.size
    bw = min(w - 2, sz * 8 + sz + 1)
    sy = max(2, (h - (sz + 2)) // 2)
    sx = max(1, (w - bw) // 2)
    cw = max(bw // sz, 4)

    # Top info bar
    info = f'Score:{game.score:>6}  Best:{game.best_score:>6}  Max:{game.get_max_tile()}  Tiles:{game.tile_count()}  Mv:{game.total_moves}'
    if game.over:
        info += '  GAME OVER'
    elif game.won:
        info += '  You Win!  (C=continue)'
    try:
        stdscr.addnstr(0, 0, info.ljust(w - 1)[:MAX_W], w - 1,
                       curses.color_pair(_ensure_pair(curses.COLOR_BLACK, curses.COLOR_CYAN))
                       | curses.A_BOLD)
    except curses.error:
        pass

    border = '+' + '-' * (bw - 2) + '+'

    # Draw top border
    try:
        stdscr.addnstr(sy, sx, border[:bw], bw,
                       curses.color_pair(0) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw cells
    for r in range(sz):
        y = sy + 1 + r
        for c in range(sz):
            val = game.grid[r][c]
            txt = str(val).center(cw - 1) if val else ' ' * cw
            fg, bg = _TILE_PALETTE.get(val, (curses.COLOR_BLACK, curses.COLOR_MAGENTA))
            pair = _ensure_pair(fg, bg)
            # Flash merged tiles bright
            if (r, c) in game._flash_map:
                pair = _ensure_pair(curses.COLOR_YELLOW, curses.COLOR_WHITE)
                txt = txt.upper()
            try:
                stdscr.addnstr(y, sx + 1 + c * cw, txt[:cw - 1], cw - 1,
                               curses.color_pair(pair))
            except curses.error:
                pass
        # Row separator
        if r < sz - 1:
            try:
                stdscr.addnstr(y + 1, sx, border[:bw], bw,
                               curses.color_pair(0) | curses.A_BOLD)
            except curses.error:
                pass

    # Bottom border
    try:
        stdscr.addnstr(sy + sz + 1, sx, border[:bw], bw,
                       curses.color_pair(0) | curses.A_BOLD)
    except curses.error:
        pass

    # Controls hint bar
    controls = 'Arrow Keys:move  R:new  Q:quit  u:undo  h:hint  p:pause'
    try:
        stdscr.addnstr(h - 2, 0, controls.ljust(w - 1)[:MAX_W], w - 1,
                       curses.A_DIM)
    except curses.error:
        pass

    # Hint / status bar
    tip = ''
    if game.can_undo:
        tip += '[U]ndo  '
    hint = game.find_hint()
    if hint:
        tip += f'Hint:{hint.capitalize()}  '
    try:
        stdscr.addnstr(h - 1, 0, tip[:MAX_W].ljust(w - 1), w - 1,
                       curses.A_DIM | curses.A_UNDERLINE)
    except curses.error:
        pass

    stdscr.refresh()


class InputHandler:
    """Rate-limited input reader to prevent key-repeat flooding."""

    def __init__(self, debounce_ms=60):
        self._lt = 0.0
        self._deb_ms = debounce_ms
        self.paused = False

    def get_key(self, stdscr, timeout_ms=100):
        if self.paused:
            stdscr.nodelay(False)
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q'), 27):
                self.paused = False
            return None
        stdscr.nodelay(True)
        now = time.time()
        if now - self._lt < self._deb_ms / 1000:
            stdscr.getch()  # drain excess
            return None
        ch = stdscr.getch()
        if ch == -1:
            return None
        self._lt = now
        return ch


def run_game_curses(stdscr, size=4):
    game = GameEngine(size)
    inp = InputHandler()
    while True:
        render_board(stdscr, game)
        ch = inp.get_key(stdscr)
        if ch is None or ch == -1:
            continue
        if ch in (ord('q'), ord('Q')):
            break
        if ch in (ord('r'), ord('R')):
            game.reset()
            continue
        if ch in (ord('u'), ord('U')) and game.can_undo:
            game.undo()
            continue
        if ch in (ord('p'), ord('P')):
            inp.paused = True
            render_board(stdscr, game)
            continue
        if ch in (ord('c'), ord('C')) and game.won:
            game.continue_after_win = True
            continue
        d = KEY_TO_DIR.get(ch)
        if d:
            game.move(d)


def main():
    parser = argparse.ArgumentParser(description='CLI 2048 Puzzle Game')
    parser.add_argument('--size', type=int, default=4, choices=[3, 4, 5, 6],
                        help='Grid size (3-6)')
    args = parser.parse_args()
    curses.wrapper(lambda s: run_game_curses(s, size=args.size))


if __name__ == '__main__':
    main()
