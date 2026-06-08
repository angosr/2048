#!/usr/bin/env python3
"""CLI 2048 Game - Feature-rich terminal implementation with undo, hints, save/load, pause,
statistics, timer, difficulty levels, auto-save, adaptive AI hints, and color themes."""

import argparse
import curses
import json
import math
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

# --- Configuration & Constants ---
MIN_WIDTH = 25
MIN_HEIGHT = 12
SAVE_PATH = Path.home() / ".2048_save.json"
AUTOSAVE_PATH = Path.home() / ".2048_autosave.json"
BEST_SCORE_PATH = Path.home() / ".2048_best_score"
INPUT_THROTTLE_MS = 60  # milliseconds between inputs

# Difficulty presets: (prob_2, prob_4) — rest spawns nothing (stays empty, no tile)
# In "hard" mode, 4-tiles spawn more often making the game harder.
DIFFICULTY_PRESETS = {
    "easy":   {"p2": 0.95, "p4": 0.05},
    "normal": {"p2": 0.90, "p4": 0.10},
    "hard":   {"p2": 0.80, "p4": 0.20},
}

# Color themes
THEMES = {
    "classic": [
        (0,    curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (2,    curses.COLOR_WHITE,  curses.COLOR_BLUE),
        (4,    curses.COLOR_WHITE,  curses.COLOR_MAGENTA),
        (8,    curses.COLOR_WHITE,  curses.COLOR_RED),
        (16,   curses.COLOR_WHITE,  curses.COLOR_RED),
        (32,   curses.COLOR_WHITE,  curses.COLOR_RED),
        (64,   curses.COLOR_WHITE,  curses.COLOR_RED),
        (128,  curses.COLOR_WHITE,  curses.COLOR_YELLOW),
        (256,  curses.COLOR_WHITE,  curses.COLOR_YELLOW),
        (512,  curses.COLOR_WHITE,  curses.COLOR_YELLOW),
        (1024, curses.COLOR_WHITE,  curses.COLOR_CYAN),
        (2048, curses.COLOR_WHITE,  curses.COLOR_GREEN),
        (4096, curses.COLOR_WHITE,  curses.COLOR_BLUE),
    ],
    "monochrome": [
        (0,    curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (2,    curses.COLOR_BLACK,  curses.COLOR_WHITE),
        (4,    curses.COLOR_BLACK,  curses.COLOR_WHITE),
        (8,    curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (16,   curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (32,   curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (64,   curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (128,  curses.COLOR_BLACK,  curses.COLOR_WHITE),
        (256,  curses.COLOR_BLACK,  curses.COLOR_WHITE),
        (512,  curses.COLOR_BLACK,  curses.COLOR_WHITE),
        (1024, curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (2048, curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (4096, curses.COLOR_WHITE,  curses.COLOR_BLACK),
    ],
    "warm": [
        (0,    curses.COLOR_WHITE,  curses.COLOR_BLACK),
        (2,    curses.COLOR_WHITE,  curses.COLOR_RED),
        (4,    curses.COLOR_WHITE,  curses.COLOR_RED),
        (8,    curses.COLOR_WHITE,  curses.COLOR_MAGENTA),
        (16,   curses.COLOR_WHITE,  curses.COLOR_MAGENTA),
        (32,   curses.COLOR_WHITE,  curses.COLOR_MAGENTA),
        (64,   curses.COLOR_WHITE,  curses.COLOR_MAGENTA),
        (128,  curses.COLOR_WHITE,  curses.COLOR_RED),
        (256,  curses.COLOR_WHITE,  curses.COLOR_RED),
        (512,  curses.COLOR_WHITE,  curses.COLOR_RED),
        (1024, curses.COLOR_WHITE,  curses.COLOR_YELLOW),
        (2048, curses.COLOR_WHITE,  curses.COLOR_YELLOW),
        (4096, curses.COLOR_WHITE,  curses.COLOR_YELLOW),
    ],
}


def init_colors(theme_name="classic"):
    """Pre-initialize curses color pairs to avoid runtime crashes.

    Returns a dict mapping tile values to initialized color pair IDs.
    """
    curses.start_color()
    curses.use_default_colors()

    color_map = {}
    pair_id = 1

    tile_configs = THEMES.get(theme_name, THEMES["classic"])

    for val, fg, bg in tile_configs:
        try:
            curses.init_pair(pair_id, fg, bg)
            color_map[val] = pair_id
            pair_id += 1
        except curses.error:
            color_map[val] = 1

    return color_map


def format_score(score):
    """Return score string with thousands separator."""
    return f"{score:,}"


def format_time(seconds):
    """Return mm:ss or hh:mm:ss formatted time string."""
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class Game:
    """Core 2048 game logic with state tracking for undo, save/load, and statistics."""

    def __init__(self, size=4, difficulty="normal"):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.score = 0
        self.best_score = self._load_best_score()
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.undo_stack = []
        self.moves = 0
        self.paused = False
        self.flash_cell = None  # (row, col) of last merge for animation
        self.difficulty = difficulty
        self._diff_cfg = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["normal"])
        # Timer
        self.start_time = time.time()
        self.elapsed_paused = 0.0  # accumulated time while paused
        self._pause_start = None

    def _load_best_score(self):
        """Load best score from local file system."""
        if BEST_SCORE_PATH.exists():
            try:
                return int(BEST_SCORE_PATH.read_text().strip())
            except (ValueError, IOError):
                return 0
        return 0

    def _save_best_score(self):
        """Persist best score to disk if exceeded."""
        if self.score > self.best_score:
            self.best_score = self.score
            try:
                BEST_SCORE_PATH.touch(exist_ok=True)
                BEST_SCORE_PATH.write_text(str(self.best_score))
            except IOError:
                pass

    def get_elapsed_time(self):
        """Return total seconds played (excluding paused time)."""
        total = time.time() - self.start_time - self.elapsed_paused
        if self._pause_start is not None:
            total -= (time.time() - self._pause_start)
        return max(0.0, total)

    def _push_state(self):
        """Push current game state onto the undo history stack (max 20 entries)."""
        self.undo_stack.append({
            'grid': deepcopy(self.grid),
            'score': self.score,
            'won': self.won,
            'moves': self.moves,
        })
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)

    def undo(self):
        """Revert to the previously saved state. Returns True if successful."""
        if not self.undo_stack:
            return False
        state = self.undo_stack.pop()
        self.grid = state['grid']
        self.score = state['score']
        self.won = state['won']
        self.moves = state['moves']
        self.over = False
        self.flash_cell = None
        return True

    def new_game(self):
        """Reset all game variables and spawn starting tiles."""
        self.grid = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.undo_stack.clear()
        self.moves = 0
        self.paused = False
        self.flash_cell = None
        self.start_time = time.time()
        self.elapsed_paused = 0.0
        self._pause_start = None
        self.add_random_tile()
        self.add_random_tile()

    def toggle_pause(self):
        """Toggle pause state, tracking elapsed time correctly."""
        if self.paused:
            # Resume
            if self._pause_start is not None:
                self.elapsed_paused += time.time() - self._pause_start
                self._pause_start = None
            self.paused = False
        else:
            self._pause_start = time.time()
            self.paused = True

    def add_random_tile(self):
        """Add a tile to a random empty cell according to difficulty settings."""
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.grid[r][c] == 0]
        if not empty_cells:
            return
        r, c = random.choice(empty_cells)
        roll = random.random()
        p2 = self._diff_cfg["p2"]
        self.grid[r][c] = 2 if roll < p2 else 4

    def _slide_row_left(self, row):
        """Compact, merge, and pad a single list representing a row."""
        filtered = [x for x in row if x != 0]
        merged = []
        points = 0
        i = 0
        while i < len(filtered):
            if i + 1 < len(filtered) and filtered[i] == filtered[i + 1]:
                val = filtered[i] * 2
                merged.append(val)
                points += val
                i += 2
            else:
                merged.append(filtered[i])
                i += 1
        merged.extend([0] * (self.size - len(merged)))
        return merged, points

    def move(self, direction):
        """Process directional input. Returns True if board changed."""
        if self.paused or self.over:
            return False

        old_grid = deepcopy(self.grid)
        total_points = 0
        self.flash_cell = None

        if direction == "left":
            for r in range(self.size):
                new_row, pts = self._slide_row_left(self.grid[r])
                self.grid[r] = new_row
                total_points += pts

        elif direction == "right":
            for r in range(self.size):
                new_row, pts = self._slide_row_left(self.grid[r][::-1])
                self.grid[r] = new_row[::-1]
                total_points += pts

        elif direction == "up":
            for c in range(self.size):
                col = [self.grid[r][c] for r in range(self.size)]
                new_col, pts = self._slide_row_left(col)
                for r in range(self.size):
                    self.grid[r][c] = new_col[r]
                total_points += pts

        elif direction == "down":
            for c in range(self.size):
                col = [self.grid[r][c] for r in range(self.size)][::-1]
                new_col, pts = self._slide_row_left(col)
                new_col = new_col[::-1]
                for r in range(self.size):
                    self.grid[r][c] = new_col[r]
                total_points += pts

        changed = self.grid != old_grid
        if changed:
            self._push_state()
            self.score += total_points
            self.moves += 1
            self.add_random_tile()
            self._check_state()

            if self.continue_after_win:
                self.won = False

            self._save_best_score()

        return changed

    def _check_state(self):
        """Evaluate win/loss conditions post-move."""
        if not self.won and not self.continue_after_win:
            for r in range(self.size):
                for c in range(self.size):
                    if self.grid[r][c] == 2048:
                        self.won = True

        if not self.over and self._has_empty_cell():
            return

        if not self.over and self._can_merge():
            return

        self.over = True

    def _has_empty_cell(self):
        """Check if any empty cell exists."""
        return any(self.grid[r][c] == 0 for r in range(self.size) for c in range(self.size))

    def _can_merge(self):
        """Check if any adjacent tiles can merge."""
        for r in range(self.size):
            for c in range(self.size):
                val = self.grid[r][c]
                if c + 1 < self.size and self.grid[r][c + 1] == val:
                    return True
                if r + 1 < self.size and self.grid[r + 1][c] == val:
                    return True
        return False

    def get_hint(self):
        """Return the best move direction using an improved heuristic.

        Evaluates each direction using:
        - Empty cell bonus (mobility)
        - Monotonicity (reward tiles ordered in one direction along rows/cols)
        - Merge potential (reward adjacent equal tiles)
        - Corner bonus (reward keeping highest tile in a corner)

        Looks 1-ply deep (simulates the move, then evaluates resulting position).
        Returns direction string or None if no move is possible.
        """
        if self.over or self.paused:
            return None

        best_dir = None
        best_score = -float('inf')

        for direction in ["up", "down", "left", "right"]:
            test_grid = deepcopy(self.grid)
            changed, pts = self._simulate_move(test_grid, direction)
            if not changed:
                continue

            score = self._evaluate_grid(test_grid) + pts * 0.5
            if score > best_score:
                best_score = score
                best_dir = direction

        return best_dir

    def _evaluate_grid(self, grid):
        """Heuristic evaluation of a grid state.

        Combines: empty cells, monotonicity, merge potential, smoothness, corner bonus.
        """
        size = self.size
        empty = 0
        merge_score = 0.0
        mono_score = 0.0
        smoothness = 0.0
        max_val = 0
        max_pos = None

        for r in range(size):
            for c in range(size):
                v = grid[r][c]
                if v == 0:
                    empty += 1
                    continue
                if v > max_val:
                    max_val = v
                    max_pos = (r, c)
                # Merge potential: adjacent equal tiles
                if c + 1 < size and grid[r][c + 1] == v:
                    merge_score += v
                if r + 1 < size and grid[r + 1][c] == v:
                    merge_score += v

        # Empty cell bonus (log scale to avoid over-valuing emptiness)
        empty_score = math.log2(empty + 1) * 2.7

        # Monotonicity: check each row and column for ordered sequences
        for r in range(size):
            row_vals = [grid[r][c] for c in range(size) if grid[r][c] > 0]
            mono_score += self._monotonicity_score(row_vals)
        for c in range(size):
            col_vals = [grid[r][c] for r in range(size) if grid[r][c] > 0]
            mono_score += self._monotonicity_score(col_vals)

        # Smoothness: penalize large differences between adjacent tiles
        for r in range(size):
            for c in range(size):
                v = grid[r][c]
                if v == 0:
                    continue
                if c + 1 < size and grid[r][c + 1] > 0:
                    ratio = abs(math.log2(v) - math.log2(grid[r][c + 1]))
                    smoothness -= ratio
                if r + 1 < size and grid[r + 1][c] > 0:
                    ratio = abs(math.log2(v) - math.log2(grid[r + 1][c]))
                    smoothness -= ratio

        # Corner bonus: reward keeping the highest tile in a corner
        corner_bonus = 0.0
        if max_pos is not None:
            corners = [(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)]
            if max_pos in corners:
                corner_bonus = math.log2(max_val) * 1.5

        return empty_score + merge_score * 1.0 + mono_score * 1.0 + smoothness * 0.1 + corner_bonus

    @staticmethod
    def _monotonicity_score(vals):
        """Score how monotonic a sequence is (higher = more ordered)."""
        if len(vals) < 2:
            return 0.0
        inc = 0.0
        dec = 0.0
        for i in range(len(vals) - 1):
            a = math.log2(vals[i]) if vals[i] > 0 else 0
            b = math.log2(vals[i + 1]) if vals[i + 1] > 0 else 0
            if a <= b:
                inc += (b - a)
            else:
                dec += (a - b)
        # Reward the dominant direction
        return max(inc, dec) - min(inc, dec) * 0.5

    def _simulate_move(self, grid, direction):
        """Simulate a move on the given grid without modifying game state. Returns (changed, points)."""
        old_grid = deepcopy(grid)
        total_points = 0

        if direction == "left":
            for r in range(self.size):
                grid[r], pts = self._slide_row_left(grid[r])
                total_points += pts
        elif direction == "right":
            for r in range(self.size):
                new_row, pts = self._slide_row_left(grid[r][::-1])
                grid[r] = new_row[::-1]
                total_points += pts
        elif direction == "up":
            for c in range(self.size):
                col = [grid[r][c] for r in range(self.size)]
                new_col, pts = self._slide_row_left(col)
                for r in range(self.size):
                    grid[r][c] = new_col[r]
                total_points += pts
        elif direction == "down":
            for c in range(self.size):
                col = [grid[r][c] for r in range(self.size)][::-1]
                new_col, pts = self._slide_row_left(col)
                new_col = new_col[::-1]
                for r in range(self.size):
                    grid[r][c] = new_col[r]
                total_points += pts

        return grid != old_grid, total_points

    def save_game(self, path=None):
        """Save current game state to disk. Returns True if successful."""
        save_path = path or SAVE_PATH
        state = {
            'grid': self.grid,
            'score': self.score,
            'best_score': self.best_score,
            'won': self.won,
            'over': self.over,
            'continue_after_win': self.continue_after_win,
            'moves': self.moves,
            'size': self.size,
            'difficulty': self.difficulty,
            'elapsed': self.get_elapsed_time(),
        }
        try:
            save_path.write_text(json.dumps(state, indent=2))
            return True
        except IOError:
            return False

    def load_game(self, path=None):
        """Load game state from disk. Returns True if successful."""
        load_path = path or SAVE_PATH
        if not load_path.exists():
            return False
        try:
            data = json.loads(load_path.read_text())
            self.size = data.get('size', 4)
            self.grid = data['grid']
            self.score = data['score']
            self.best_score = data.get('best_score', self.best_score)
            self.won = data.get('won', False)
            self.over = data.get('over', False)
            self.continue_after_win = data.get('continue_after_win', False)
            self.moves = data.get('moves', 0)
            self.difficulty = data.get('difficulty', 'normal')
            self._diff_cfg = DIFFICULTY_PRESETS.get(self.difficulty, DIFFICULTY_PRESETS["normal"])
            self.undo_stack.clear()
            self.paused = False
            self.flash_cell = None
            # Restore timer
            elapsed = data.get('elapsed', 0.0)
            self.start_time = time.time() - elapsed
            self.elapsed_paused = 0.0
            self._pause_start = None
            return True
        except (IOError, json.JSONDecodeError, KeyError):
            return False

    def autosave(self):
        """Auto-save current state for recovery."""
        return self.save_game(path=AUTOSAVE_PATH)

    def load_autosave(self):
        """Load autosave if available. Returns True if loaded."""
        if self.load_game(path=AUTOSAVE_PATH):
            try:
                AUTOSAVE_PATH.unlink(missing_ok=True)
            except (IOError, TypeError):
                try:
                    AUTOSAVE_PATH.unlink()
                except IOError:
                    pass
            return True
        return False

    def has_autosave(self):
        """Check if an autosave file exists."""
        return AUTOSAVE_PATH.exists()

    def get_stats(self):
        """Return a dict of game statistics."""
        tiles = []
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] > 0:
                    tiles.append(self.grid[r][c])

        max_tile = max(tiles) if tiles else 0
        avg_tile = sum(tiles) // len(tiles) if tiles else 0

        return {
            'score': self.score,
            'best': self.best_score,
            'max': max_tile,
            'avg': avg_tile,
            'tiles': len(tiles),
            'moves': self.moves,
            'elapsed': self.get_elapsed_time(),
            'difficulty': self.difficulty,
        }

    def get_grid(self):
        """Return a deep copy of the current grid."""
        return deepcopy(self.grid)

    def get_score(self):
        """Return current score."""
        return self.score

    def get_best_score(self):
        """Return best score achieved."""
        return self.best_score

    def is_over(self):
        """Return True if game is over (no moves left)."""
        return self.over

    def is_won(self):
        """Return True if 2048 tile reached (and not continuing)."""
        return self.won


# --- Curses Rendering ---

ARROW_MAP = {
    "up": "\u2191",
    "down": "\u2193",
    "left": "\u2190",
    "right": "\u2192",
}


def _tile_attr(val, color_map):
    """Return curses attribute for a tile value — bold for high values."""
    pair_id = color_map.get(val, 1)
    attr = curses.color_pair(pair_id)
    if val >= 128:
        attr |= curses.A_BOLD
    if val >= 1024:
        attr |= curses.A_BOLD | curses.A_STANDOUT
    return attr


def draw_board(stdscr, game, color_map, status_msg="", hint_dir=None):
    """Render the game board with dynamic layout and graceful resize handling."""
    stdscr.erase()

    height, width = stdscr.getmaxyx()

    # Graceful handling of overly small terminal windows
    if height < MIN_HEIGHT or width < MIN_WIDTH:
        msg = " Terminal too small! Resize to play. "
        y, x = height // 2, width // 2
        try:
            stdscr.addnstr(y, max(0, x - len(msg) // 2), msg, width - 2, curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()
        return

    grid = game.get_grid()
    size = len(grid)

    # Dynamic layout calculation
    cell_h = 1
    cell_w = max(6, min(10, (width - 4) // (size + 1)))

    grid_start_y = 5
    grid_start_x = max(1, (width - (size * (cell_w + 2) + 2)) // 2)

    # Title
    title = "CLI 2048"
    diff_tag = f" [{game.difficulty.upper()}]"
    title_full = title + diff_tag
    try:
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addnstr(1, max(0, (width - len(title_full)) // 2), title_full, width - 2)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass

    # Statistics bar (line 2)
    stats = game.get_stats()
    time_str = format_time(stats['elapsed'])
    stats_str = (
        f"Score: {format_score(stats['score']):<10} "
        f"Best: {format_score(stats['best']):<10} "
        f"Max: {stats['max']:<5} "
        f"Avg: {stats['avg']:<5} "
        f"Mv: {stats['moves']:<5} "
        f"T: {time_str}"
    )
    try:
        stdscr.addnstr(2, max(0, (width - len(stats_str)) // 2), stats_str, width - 2)
    except curses.error:
        pass

    # Undo count indicator (line 3)
    undo_count = len(game.undo_stack)
    undo_str = f"Undo: {undo_count}/20"
    if undo_count > 0:
        undo_str += "  [u to undo]"
    try:
        stdscr.addnstr(3, max(0, (width - len(undo_str)) // 2), undo_str, width - 2, curses.A_DIM)
    except curses.error:
        pass

    # Grid top border
    top_border = "+" + ("+" + "-" * cell_w) * size + "+"
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addnstr(grid_start_y, grid_start_x, top_border, width - 2)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass

    # Draw rows and cells
    for r in range(size):
        row_y = grid_start_y + 1 + r * (cell_h + 1)

        # Row left border
        try:
            stdscr.addch(row_y, grid_start_x, "|", curses.A_BOLD)
        except curses.error:
            pass

        for c in range(size):
            val = grid[r][c]
            cell_x = grid_start_x + c * (cell_w + 2) + 1

            attr = _tile_attr(val, color_map)
            val_str = str(val).center(cell_w) if val > 0 else " " * cell_w
            try:
                stdscr.addnstr(row_y, cell_x, val_str, cell_w, attr)
            except curses.error:
                pass

        # Row right border
        try:
            stdscr.addch(row_y, grid_start_x + size * (cell_w + 2), "|", curses.A_BOLD)
        except curses.error:
            pass

    # Grid bottom border
    bottom_y = grid_start_y + 1 + size * (cell_h + 1)
    bottom_border = "+" + ("+" + "-" * cell_w) * size + "+"
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addnstr(bottom_y, grid_start_x, bottom_border, width - 2)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass

    # Status messages
    status_y = bottom_y + 2
    if game.paused:
        msg = "PAUSED - Press 'p' to resume"
        try:
            stdscr.addnstr(status_y, max(0, (width - len(msg)) // 2), msg, width - 2,
                           curses.A_BOLD | curses.A_REVERSE)
        except curses.error:
            pass
    elif game.is_won() and not game.is_over():
        msg = "You reached 2048! Press 'c' to continue, 'q' to quit."
        try:
            stdscr.addnstr(status_y, max(0, (width - len(msg)) // 2), msg, width - 2,
                           curses.color_pair(color_map.get(2048, 1)) | curses.A_BOLD)
        except curses.error:
            pass
    elif game.is_over():
        msg = f"Game Over! Score: {format_score(game.get_score())} | 'r': restart, 'q': quit"
        try:
            stdscr.addnstr(status_y, max(0, (width - len(msg)) // 2), msg, width - 2,
                           curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint display
    hint_y = status_y + 1
    if hint_dir:
        arrow = ARROW_MAP.get(hint_dir, hint_dir)
        hint_msg = f"Hint: move {hint_dir} {arrow}"
        try:
            stdscr.addnstr(hint_y, max(0, (width - len(hint_msg)) // 2), hint_msg, width - 2,
                           curses.color_pair(color_map.get(2048, 1)) | curses.A_BOLD)
        except curses.error:
            pass

    # Status message (save/load feedback etc.)
    msg_y = status_y + 2 if not hint_dir else status_y + 2
    if status_msg:
        try:
            stdscr.addnstr(msg_y, max(0, (width - len(status_msg)) // 2), status_msg, width - 2,
                           curses.A_DIM)
        except curses.error:
            pass

    # Instructions
    instr_y = (height - 2) if height > MIN_HEIGHT + 4 else msg_y + 2
    instr = "Arrows/WASD/HJKL: Move | u:Undo h:Hint p:Pause s:Save l:Load r:New q:Quit"
    try:
        stdscr.addnstr(instr_y, max(0, (width - len(instr)) // 2), instr, width - 2, curses.A_DIM)
    except curses.error:
        pass

    stdscr.refresh()


def main(stdscr, size=4, difficulty="normal", theme="classic", recover=False):
    """Main game loop with input handling, throttling, and all features."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)

    # Initialize color pairs
    color_map = init_colors(theme)

    # Create game instance
    game = Game(size=size, difficulty=difficulty)

    # Try to recover autosave if requested
    if recover and game.has_autosave():
        if game.load_autosave():
            pass  # recovered
        else:
            game.new_game()
    else:
        game.new_game()

    status_msg = ""
    if recover and game.has_autosave():
        status_msg = ""  # cleared after load

    hint_dir = None
    last_input_time = 0

    while True:
        draw_board(stdscr, game, color_map, status_msg=status_msg, hint_dir=hint_dir)
        status_msg = ""  # Clear status after one draw
        hint_dir = None  # Clear hint after one draw

        key = stdscr.getch()

        # Input throttling
        now = time.time() * 1000
        if now - last_input_time < INPUT_THROTTLE_MS:
            continue
        last_input_time = now

        # Quit — autosave before exit if game is active
        if key == ord('q') or key == ord('Q'):
            if not game.is_over():
                game.autosave()
            break

        # New game
        elif key == ord('r') or key == ord('R'):
            game.new_game()

        # Continue after winning
        elif key == ord('c') or key == ord('C'):
            game.continue_after_win = True
            game.won = False

        # Undo
        elif key in (ord('u'), ord('U')):
            if game.undo():
                status_msg = "Undo successful."
            else:
                status_msg = "Nothing to undo."

        # Pause/Resume
        elif key in (ord('p'), ord('P')):
            game.toggle_pause()
            status_msg = "Resumed." if not game.paused else ""

        # Hint (lowercase h or ?)
        elif key in (ord('h'), ord('?')):
            hint_dir = game.get_hint()
            if hint_dir:
                status_msg = f"Suggested: {hint_dir}"
            else:
                status_msg = "No hint available."

        # Save (lowercase s)
        elif key == ord('s'):
            if game.save_game():
                status_msg = f"Game saved to {SAVE_PATH}"
            else:
                status_msg = "Failed to save game."

        # Load (lowercase l)
        elif key == ord('l'):
            if game.load_game():
                status_msg = "Game loaded successfully."
            else:
                status_msg = "No saved game found or load failed."

        # Movement: Arrow keys, WASD, Vim keys (HJKL - uppercase)
        # Arrow keys + WASD always work for movement
        # Vim: H=left, J=down, K=up, L=right
        elif key in (curses.KEY_UP, ord('w'), ord('W'), ord('k'), ord('K')):
            game.move("up")
        elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
            game.move("down")
        elif key in (curses.KEY_LEFT, ord('a'), ord('A'), ord('H')):
            game.move("left")
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D'), ord('L')):
            game.move("right")

    curses.endwin()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="CLI 2048 Game")
    parser.add_argument('--size', type=int, default=4, help='Board size (default: 4)')
    parser.add_argument('--difficulty', choices=['easy', 'normal', 'hard'], default='normal',
                        help='Game difficulty: easy/normal/hard (default: normal). '
                             'Controls spawn probability of 2 vs 4 tiles.')
    parser.add_argument('--theme', choices=list(THEMES.keys()), default='classic',
                        help='Color theme: classic/monochrome/warm (default: classic)')
    parser.add_argument('--recover', action='store_true',
                        help='Recover from autosave if available')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        curses.wrapper(lambda stdscr: main(
            stdscr,
            size=args.size,
            difficulty=args.difficulty,
            theme=args.theme,
            recover=args.recover,
        ))
    except KeyboardInterrupt:
        sys.exit(0)
