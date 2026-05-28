#!/usr/bin/env python3
"""CLI 2048 Game - A terminal-based version of the classic 2048 puzzle game."""

import curses
import os
import random
import sys
from copy import deepcopy
from pathlib import Path


class Game:
    """Core 2048 game logic."""

    def __init__(self, size=4):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.score = 0
        self.best_score = self._load_best_score()
        self.won = False
        self.over = False
        self.continue_after_win = False

    def _load_best_score(self):
        """Load best score from file."""
        save_path = Path.home() / ".2048_best_score"
        if save_path.exists():
            try:
                return int(save_path.read_text().strip())
            except (ValueError, IOError):
                return 0
        return 0

    def _save_best_score(self):
        """Save best score to file."""
        if self.score > self.best_score:
            self.best_score = self.score
            try:
                save_path = Path.home() / ".2048_best_score"
                save_path.touch(exist_ok=True)
                with open(save_path, "w") as f:
                    f.write(str(self.best_score))
            except IOError:
                pass

    def new_game(self):
        """Start a new game, reset all state."""
        self.grid = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        """Add a 2 or 4 to a random empty cell."""
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.grid[r][c] == 0]
        if not empty_cells:
            return
        r, c = random.choice(empty_cells)
        self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def _slide_row_left(self, row):
        """Slide a single row to the left, returning the new row and points earned."""
        # Remove zeros
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
        # Pad with zeros
        merged.extend([0] * (self.size - len(merged)))
        return merged, points

    def move(self, direction):
        """
        Attempt a move in the given direction.
        direction: 'up', 'down', 'left', 'right'
        Returns True if the board changed, False otherwise.
        """
        old_grid = deepcopy(self.grid)
        total_points = 0

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
            self.score += total_points
            self.add_random_tile()
            self._check_state()
            self._save_best_score()

        return changed

    def _check_state(self):
        """Check if the player has won or lost."""
        # Check for 2048 tile
        if not self.won:
            for r in range(self.size):
                for c in range(self.size):
                    if self.grid[r][c] == 2048:
                        self.won = True

        # Check for possible moves
        if not self.over and self._has_empty_cell():
            self.over = False
            return

        if not self.over and self._can_merge():
            self.over = False
            return

        self.over = True

    def _has_empty_cell(self):
        """Check if there are any empty cells."""
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == 0:
                    return True
        return False

    def _can_merge(self):
        """Check if any adjacent tiles can be merged."""
        for r in range(self.size):
            for c in range(self.size):
                val = self.grid[r][c]
                if c + 1 < self.size and self.grid[r][c + 1] == val:
                    return True
                if r + 1 < self.size and self.grid[r + 1][c] == val:
                    return True
        return False

    def get_grid(self):
        """Return the current grid state."""
        return deepcopy(self.grid)

    def get_score(self):
        """Return the current score."""
        return self.score

    def get_best_score(self):
        """Return the best score."""
        return self.best_score

    def is_over(self):
        """Check if the game is over."""
        return self.over

    def is_won(self):
        """Check if the player has reached 2048."""
        return self.won


# ─── Tile Colors ──────────────────────────────────────────────────

TILE_FG = {
    0:      curses.COLOR_BLACK,
    2:      curses.COLOR_WHITE,
    4:      curses.COLOR_WHITE,
    8:      curses.COLOR_WHITE,
    16:     curses.COLOR_WHITE,
    32:     curses.COLOR_WHITE,
    64:     curses.COLOR_RED,
    128:    curses.COLOR_YELLOW,
    256:    curses.COLOR_YELLOW,
    512:    curses.COLOR_YELLOW,
    1024:   curses.COLOR_CYAN,
    2048:   curses.COLOR_GREEN,
}

TILE_BG = {
    0:      curses.COLOR_BLACK,
    2:      curses.COLOR_BLUE,
    4:      curses.COLOR_MAGENTA,
    8:      curses.COLOR_RED,
    16:     curses.COLOR_RED,
    32:     curses.COLOR_RED,
    64:     curses.COLOR_RED,
    128:    curses.COLOR_YELLOW,
    256:    curses.COLOR_YELLOW,
    512:    curses.COLOR_YELLOW,
    1024:   curses.COLOR_CYAN,
    2048:   curses.COLOR_GREEN,
}


def get_tile_color(value):
    """Get foreground/background color for a tile value."""
    fg = TILE_FG.get(value, curses.COLOR_WHITE)
    bg = TILE_BG.get(value, curses.COLOR_BLUE)
    return fg, bg


# ─── Curses Rendering ─────────────────────────────────────────────

def draw_board(stdscr, game):
    """Draw the game board with colors using curses."""
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pairs
    for fg in [curses.COLOR_WHITE, curses.COLOR_BLACK, curses.COLOR_RED,
               curses.COLOR_YELLOW, curses.COLOR_CYAN, curses.COLOR_GREEN]:
        for bg in [curses.COLOR_BLUE, curses.COLOR_MAGENTA, curses.COLOR_RED,
                   curses.COLOR_YELLOW, curses.COLOR_BLACK, curses.COLOR_GREEN]:
            curses.init_pair(curses.color_pair_id(fg, bg), fg, bg)

    height, width = stdscr.getmaxyx()

    # Clear screen
    stdscr.erase()

    grid = game.get_grid()
    size = len(grid)

    # Calculate cell dimensions based on available space
    max_cell_width = 8
    min_cell_height = 1

    # Title
    title = "  CLI 2048  "
    title_y = 1
    if title:
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addnstr(title_y, max(0, (width - len(title)) // 2), title, width - 2, curses.color_pair(1) | curses.A_BOLD)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    # Score display
    score_str = f"Score: {game.get_score()}   Best: {game.get_best_score()}"
    score_y = 3
    stdscr.addnstr(score_y, max(0, (width - len(score_str)) // 2), score_str, width - 2)

    # Determine grid position
    # Each row takes up min_cell_height lines, each cell takes up max_cell_width characters
    cell_h = min(min_cell_height, max(1, (height - 10) // size))
    cell_w = min(max_cell_width, max(6, (width - 4) // (size + 1)))

    # Draw grid header (top border)
    grid_start_y = 5
    grid_start_x = (width - size * (cell_w + 2)) // 2

    # Top border
    top_border = "+" + ("+" + "-" * cell_w) * size + "+"
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addnstr(grid_start_y, grid_start_x, top_border, width - 2)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass

    # Draw rows
    for r in range(size):
        row_y = grid_start_y + 1 + r * (cell_h + 1)

        # Left border
        try:
            stdscr.addch(row_y, grid_start_x, "|", curses.A_BOLD)
        except curses.error:
            pass

        for c in range(size):
            val = grid[r][c]
            cell_x = grid_start_x + c * (cell_w + 2) + 1

            if val == 0:
                # Empty cell
                cell_bg = curses.COLOR_BLACK
                cell_fg = curses.COLOR_WHITE
            else:
                cell_fg, cell_bg = get_tile_color(val)

            try:
                color_pair = curses.color_pair(curses.color_pair_index(cell_fg, cell_bg))
                stdscr.attron(color_pair)
                val_str = str(val).center(cell_w)
                stdscr.addnstr(row_y, cell_x, val_str, cell_w, color_pair)
                stdscr.attroff(color_pair)
            except curses.error:
                pass

        # Right border
        right_border_x = grid_start_x + size * (cell_w + 2)
        try:
            stdscr.addch(row_y, right_border_x, "|", curses.A_BOLD)
        except curses.error:
            pass

    # Bottom border
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

    if game.is_won() and not game.is_over():
        msg = " You reached 2048! Press c to continue or q to quit. "
        try:
            stdscr.attron(curses.color_pair(14) | curses.A_BOLD)  # Green bold
            stdscr.addnstr(status_y, max(0, (width - len(msg)) // 2), msg, width - 2,
                          curses.color_pair(14) | curses.A_BOLD)
            stdscr.attroff(curses.color_pair(14) | curses.A_BOLD)
        except curses.error:
            pass
    elif game.is_over():
        msg = f" Game Over! Final Score: {game.get_score()} - Press r to restart, q to quit. "
        try:
            stdscr.attron(curses.color_pair(4) | curses.A_BOLD)  # Red bold
            stdscr.addnstr(status_y, max(0, (width - len(msg)) // 2), msg, width - 2,
                          curses.color_pair(4) | curses.A_BOLD)
            stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass

    # Instructions
    instr_y = status_y + 2
    instr = "Arrow keys/WASD: Move | r: New Game | q: Quit"
    try:
        stdscr.attron(curses.A_DIM)
        stdscr.addnstr(instr_y, max(0, (width - len(instr)) // 2), instr, width - 2, curses.A_DIM)
        stdscr.attroff(curses.A_DIM)
    except curses.error:
        pass

    stdscr.refresh()


def get_color_pair_index(fg, bg):
    """Map color pair to an integer index."""
    # Build a unique key for this color pair
    return hash((fg, bg)) % 100 + 1


# ─── Color Pair Management ────────────────────────────────────────

# Pre-compute color pairs for common tiles
_COLOR_PAIRS_CACHE = {}
_COLOR_COUNTER = [1]


def get_or_create_color_pair(stdscr, fg, bg):
    """Get or create a curses color pair and return its ID."""
    # Ensure colors are initialized
    if not curses.has_colors():
        return curses.A_NORMAL

    curses.start_color()
    curses.use_default_colors()

    cache_key = (fg, bg)
    if cache_key in _COLOR_PAIRS_CACHE:
        return _COLOR_PAIRS_CACHE[cache_key]

    if _COLOR_COUNTER[0] > 255:
        return curses.A_NORMAL

    pair_id = _COLOR_COUNTER[0]
    _COLOR_COUNTER[0] += 1
    curses.init_pair(pair_id, fg, bg)
    _COLOR_PAIRS_CACHE[cache_key] = pair_id
    return pair_id


# ─── Improved Rendering ──────────────────────────────────────────

def draw_board_improved(stdscr, game):
    """Draw the game board with improved colors."""
    if not curses.has_colors():
        return _draw_board_ascii(stdscr, game)

    curses.start_color()
    curses.use_default_colors()

    height, width = stdscr.getmaxyx()
    if height < 15 or width < 40:
        try:
            stdscr.clear()
            stdscr.addstr(0, 0, "Terminal too small! Need at least 40x15.")
            stdscr.refresh()
        except curses.error:
            pass
        return

    stdscr.erase()

    grid = game.get_grid()
    size = len(grid)

    # Title
    title = "  2 0 4 8  "
    try:
        stdscr.attron(curses.A_BOLD | curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_WHITE, curses.COLOR_BLUE)))
        mid = max(0, (width - len(title)) // 2)
        stdscr.addnstr(0, mid, title, width - 2)
        stdscr.attroff(curses.A_BOLD | curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_WHITE, curses.COLOR_BLUE)))
    except curses.error:
        pass

    # Score line
    score_line = f"Score: {game.get_score()}      Best: {game.get_best_score()}"
    try:
        mid = max(0, (width - len(score_line)) // 2)
        stdscr.addnstr(2, mid, score_line, width - 2)
    except curses.error:
        pass

    # Compute cell dimensions
    cell_w = min(8, max(5, (width - 8) // (size * 2)))
    cell_h = 1

    # Grid start position
    grid_w = size * (cell_w + 2) + 1
    grid_x = max(0, (width - grid_w) // 2)
    grid_y = 4

    # Top border
    top = "+" + ("-+" * size) + "-"
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addnstr(grid_y, grid_x, top, width - 2)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass

    # Draw each row
    for r in range(size):
        row_y = grid_y + 1 + r * (cell_h + 1)

        # Left wall
        try:
            stdscr.addch(row_y, grid_x, "|", curses.A_BOLD)
        except curses.error:
            pass

        for c in range(size):
            val = grid[r][c]
            cell_x = grid_x + 1 + c * (cell_w + 2)
            cell_end = cell_x + cell_w

            # Get colors for this tile
            if val == 0:
                fg, bg = curses.COLOR_WHITE, curses.COLOR_BLACK
            else:
                fg, bg = get_tile_color(val)

            pair = get_or_create_color_pair(stdscr, fg, bg)

            # Draw cell background first
            try:
                stdscr.attron(curses.color_pair(pair))
                stdscr.addnstr(row_y, cell_x, " " * cell_w, cell_w, curses.color_pair(pair))
                stdscr.attroff(curses.color_pair(pair))
            except curses.error:
                pass

            # Draw tile value centered
            if val > 0:
                val_str = str(val)
                pad_left = (cell_w - len(val_str)) // 2
                pad_right = cell_w - len(val_str) - pad_left
                content = " " * pad_left + val_str + " " * pad_right
                try:
                    stdscr.addnstr(row_y, cell_x, content, cell_w, curses.color_pair(pair) | curses.A_BOLD)
                except curses.error:
                    pass

        # Right wall
        right_x = grid_x + 1 + size * (cell_w + 2)
        try:
            stdscr.addch(row_y, right_x, "|", curses.A_BOLD)
        except curses.error:
            pass

    # Bottom border
    bottom_y = grid_y + 1 + size * (cell_h + 1)
    try:
        stdscr.attron(curses.A_BOLD)
        stdscr.addnstr(bottom_y, grid_x, top, width - 2)
        stdscr.attroff(curses.A_BOLD)
    except curses.error:
        pass

    # Status / messages
    msg_y = bottom_y + 2

    if game.is_won() and not game.is_over():
        msg = ">>> You reached 2048! Press 'c' to continue <<<"
        try:
            stdscr.attron(curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_BLACK, curses.COLOR_GREEN)) | curses.A_BOLD)
            mid = max(0, (width - len(msg)) // 2)
            stdscr.addnstr(msg_y, mid, msg, width - 2)
            stdscr.attroff(curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_BLACK, curses.COLOR_GREEN)) | curses.A_BOLD)
        except curses.error:
            pass
    elif game.is_over():
        msg = f">>> Game Over! Score: {game.get_score()} Press 'r' to restart <<<"
        try:
            stdscr.attron(curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_BLACK, curses.COLOR_RED)) | curses.A_BOLD)
            mid = max(0, (width - len(msg)) // 2)
            stdscr.addnstr(msg_y, mid, msg, width - 2)
            stdscr.attroff(curses.color_pair(get_or_create_color_pair(stdscr, curses.COLOR_BLACK, curses.COLOR_RED)) | curses.A_BOLD)
        except curses.error:
            pass

    # Controls hint
    hint = "↑↓←→/WASD: Move  |  R: New Game  |  Q: Quit"
    hint_y = msg_y + 2
    try:
        stdscr.attron(curses.A_DIM)
        mid = max(0, (width - len(hint)) // 2)
        stdscr.addnstr(hint_y, mid, hint, width - 2)
        stdscr.attroff(curses.A_DIM)
    except curses.error:
        pass

    stdscr.nodelay(False)
    stdscr.refresh()


def _draw_board_ascii(stdscr, game):
    """Fallback ASCII drawing when colors are not supported."""
    stdscr.clear()
    grid = game.get_grid()
    size = len(grid)
    cell_w = 6

    top = "+" + ("+" + "-" * cell_w) * size + "+"
    stdscr.addstr(0, 0, "2048 (No Color Support)")
    stdscr.addstr(1, 0, top)
    for r, row in enumerate(grid):
        line = "|"
        for val in row:
            if val == 0:
                line += " " * cell_w + "|"
            else:
                line += " " + str(val).ljust(cell_w - 1) + "|"
        stdscr.addstr(2 + r * 2, 0, line)
        stdscr.addstr(2 + r * 2 + 1, 0, top)

    score_line = f"Score: {game.get_score()}   Best: {game.get_best_score()}"
    stdscr.addstr(2 + size * 2 + 1, 0, score_line)
    if game.is_over():
        stdscr.addstr(2 + size * 2 + 3, 0, f"Game Over! Score: {game.get_score()}")
    stdscr.addstr(height - 2, 0, "↑↓←→/WASD: Move | R: New Game | Q: Quit")
    stdscr.refresh()


# ─── Main Game Loop ────────────────────────────────────────────────

def run_game_curses(stdscr):
    """Run the full game loop using curses."""
    # Hide cursor
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    game = Game()
    game.new_game()

    while True:
        draw_board_improved(stdscr, game)

        # Wait for input (with 100ms timeout for smooth updates)
        stdscr.nodelay(True)
        key = stdscr.getch()
        stdscr.nodelay(False)

        if key == -1:
            continue

        # Handle escape sequence for arrow keys
        if key == 27:  # Escape
            # Try to read next character
            stdscr.nodelay(True)
            key2 = stdscr.getch()
            stdscr.nodelay(False)
            if key2 == ord("["):
                stdscr.nodelay(True)
                key3 = stdscr.getch()
                stdscr.nodelay(False)
                if key3 == 65:  # Up
                    direction = "up"
                elif key3 == 66:  # Down
                    direction = "down"
                elif key3 == 67:  # Right
                    direction = "right"
                elif key3 == 68:  # Left
                    direction = "left"
                else:
                    continue
            else:
                continue
        elif key == curses.KEY_UP:
            direction = "up"
        elif key == curses.KEY_DOWN:
            direction = "down"
        elif key == curses.KEY_RIGHT:
            direction = "right"
        elif key == curses.KEY_LEFT:
            direction = "left"
        elif key in (ord('w'), ord('W')):
            direction = "up"
        elif key in (ord('s'), ord('S')):
            direction = "down"
        elif key in (ord('a'), ord('A')):
            direction = "left"
        elif key in (ord('d'), ord('D')):
            direction = "right"
        elif key in (ord('r'), ord('R')):
            game.new_game()
            continue
        elif key in (ord('q'), ord('Q')):
            break
        elif key in (ord('c'), ord('C')) and game.is_won():
            game.continue_after_win = True
            continue
        else:
            continue

        # Make the move
        moved = game.move(direction)
        if not moved:
            # Could flash the board here to indicate no move
            pass


def main():
    """Entry point."""
    print("=" * 50)
    print("       Welcome to CLI 2048!")
    print("=" * 50)
    print()
    print("Using curses mode for the best experience.")
    print("Press Ctrl+C or 'q' to quit at any time.\n")

    try:
        curses.wrapper(run_game_curses)
    except KeyboardInterrupt:
        print("\n\nThanks for playing! 👋\n")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Falling back to simple text mode...")
        try:
            play_game_simple()
        except KeyboardInterrupt:
            print("\n\nThanks for playing! 👋\n")


def play_game_simple():
    """Simple text-mode fallback for environments without curses support."""

    print("=" * 50)
    print("       Welcome to CLI 2048!")
    print("=" * 50)
    print("Note: Using simplified text mode (no curses).")
    print("Use arrow keys or WASD to move tiles.")
    print("Press 'r' for a new game, 'q' to quit.\n")

    game = Game()
    game.new_game()

    while True:
        os.system("clear" if os.name != "nt" else "cls")
        print_board(game.get_grid())
        print_status(game.get_score(), game.get_best_score(), game.is_won(), game.is_over())
        print_help()

        try:
            key = input("Enter command: ").strip().lower()
        except EOFError:
            break

        if key == "q":
            print("\nThanks for playing! Goodbye! 👋\n")
            break
        elif key == "r":
            game.new_game()
            continue

        # Map keys to directions
        move_map = {
            "w": "up",
            "s": "down",
            "a": "left",
            "d": "right",
        }

        if key == "arrow_up":
            direction = "up"
        elif key == "arrow_down":
            direction = "down"
        elif key == "arrow_left":
            direction = "left"
        elif key == "arrow_right":
            direction = "right"
        elif key in move_map:
            direction = move_map[key]
        else:
            print("\nInvalid input. Use arrow keys, WASD, 'r' for restart, or 'q' to quit.\n")
            continue

        moved = game.move(direction)
        if not moved:
            print("No move possible in that direction!\n")

        if game.is_over():
            print(f"\nGame Over! Your final score: {game.get_score()}")
            resp = input("Play again? (y/n): ").strip().lower()
            if resp == "y":
                game.new_game()
            else:
                break


# ─── Simple Display Functions ─────────────────────────────────────

def print_board(grid):
    """Print the game board as ASCII art (simple mode)."""
    size = len(grid)
    cell_width = 6
    border = "+" + ("-" * cell_width + "+") * size

    print("\n" + border)
    for row in grid:
        line = "|"
        for val in row:
            if val == 0:
                line += " " * cell_width + "|"
            else:
                val_str = str(val)
                padding = cell_width - len(val_str)
                line += " " + val_str + " " * (padding - 1) + "|"
        print(line)
    print(border + "\n")


def print_status(score, best_score, won=False, over=False):
    """Print the status bar."""
    print(f"  Score: {score:>6}  |  Best: {best_score:>6}")
    if won and not over:
        print("  🎉 You reached 2048! Keep going! 🎉")
    if over:
        print("  Game Over! Press 'r' for a new game.")


def print_help():
    """Print help information."""
    print("\nControls:")
    print("  Arrow keys / WASD — Move tiles")
    print("  r                 — New game")
    print("  q                 — Quit")
    print()


if __name__ == "__main__":
    main()
