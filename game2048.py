#!/usr/bin/env python3
"""CLI 2048 Game - Improved terminal-based version with undo, dynamic layout, and robust rendering."""

import curses
import random
import sys
from copy import deepcopy
from pathlib import Path

# --- Configuration & Constants ---
MIN_WIDTH = 25
MIN_HEIGHT = 12


def init_colors():
    """Pre-initialize curses color pairs to avoid runtime crashes.
    
    Returns a dict mapping tile values to initialized color pair IDs.
    """
    curses.start_color()
    curses.use_default_colors()
    
    color_map = {}
    pair_id = 1
    
    tile_configs = [
        (0, curses.COLOR_BLACK, curses.COLOR_BLACK),
        (2, curses.COLOR_WHITE, curses.COLOR_BLUE),
        (4, curses.COLOR_WHITE, curses.COLOR_MAGENTA),
        (8, curses.COLOR_WHITE, curses.COLOR_RED),
        (16, curses.COLOR_WHITE, curses.COLOR_RED),
        (32, curses.COLOR_WHITE, curses.COLOR_RED),
        (64, curses.COLOR_WHITE, curses.COLOR_RED),
        (128, curses.COLOR_WHITE, curses.COLOR_YELLOW),
        (256, curses.COLOR_WHITE, curses.COLOR_YELLOW),
        (512, curses.COLOR_WHITE, curses.COLOR_YELLOW),
        (1024, curses.COLOR_WHITE, curses.COLOR_CYAN),
        (2048, curses.COLOR_WHITE, curses.COLOR_GREEN),
        (4096, curses.COLOR_WHITE, curses.COLOR_BLUE),
    ]
    
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


class Game:
    """Core 2048 game logic with state tracking for Undo."""

    def __init__(self, size=4):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.score = 0
        self.best_score = self._load_best_score()
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.undo_stack = []

    def _load_best_score(self):
        """Load best score from local file system."""
        save_path = Path.home() / ".2048_best_score"
        if save_path.exists():
            try:
                return int(save_path.read_text().strip())
            except (ValueError, IOError):
                return 0
        return 0

    def _save_best_score(self):
        """Persist best score to disk if exceeded."""
        if self.score > self.best_score:
            self.best_score = self.score
            save_path = Path.home() / ".2048_best_score"
            try:
                save_path.touch(exist_ok=True)
                save_path.write_text(str(self.best_score))
            except IOError:
                pass

    def _push_state(self):
        """Push current game state onto the undo history stack (max 50 entries)."""
        self.undo_stack.append({
            'grid': deepcopy(self.grid),
            'score': self.score,
            'won': self.won
        })
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def undo(self):
        """Revert to the previously saved state. Returns True if successful."""
        if not self.undo_stack:
            return False
        state = self.undo_stack.pop()
        self.grid = state['grid']
        self.score = state['score']
        self.won = state['won']
        self.over = False
        return True

    def new_game(self):
        """Reset all game variables and spawn starting tiles."""
        self.grid = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.over = False
        self.continue_after_win = False
        self.undo_stack.clear()
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        """Add a 2 (90%) or 4 (10%) to a random empty cell."""
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.grid[r][c] == 0]
        if not empty_cells:
            return
        r, c = random.choice(empty_cells)
        self.grid[r][c] = 2 if random.random() < 0.9 else 4

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
            self._push_state()
            self.score += total_points
            self.add_random_tile()
            self._check_state()
            
            # Clear win flag if user opted to continue playing
            if self.continue_after_win:
                self.won = False
                
            self._save_best_score()

        return changed

    def _check_state(self):
        """Evaluate win/loss conditions post-move."""
        # Check victory (only if not already won or continuing)
        if not self.won and not self.continue_after_win:
            for r in range(self.size):
                for c in range(self.size):
                    if self.grid[r][c] == 2048:
                        self.won = True

        # Check stalemate
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

def draw_board(stdscr, game, color_map):
    """Render the game board with dynamic layout and graceful resize handling."""
    stdscr.erase()
    
    height, width = stdscr.getmaxyx()
    
    # Graceful handling of overly small terminal windows
    if height < MIN_HEIGHT or width < MIN_WIDTH:
        msg = " Terminal too small! Resize to play. "
        y, x = height // 2, width // 2
        try:
            stdscr.addnstr(y, max(0, x - len(msg)//2), msg, width - 2, curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()
        return

    grid = game.get_grid()
    size = len(grid)
    
    # Dynamic layout calculation
    padding_x = 4
    padding_y = 2
    available_h = height - padding_y - 4
    available_w = width - padding_x
    
    cell_h = max(1, available_h // (size + 1))
    cell_w = max(6, min(10, available_w // (size + 1)))
    
    grid_start_y = 4
    grid_start_x = max(1, (width - (size * (cell_w + 2) + 2)) // 2)
    
    # Title
    title = "CLI 2048"
    try:
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addnstr(1, max(0, (width - len(title)) // 2), title, width - 2)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass

    # Score display
    score_str = f"Score: {format_score(game.get_score()):<12}Best: {format_score(game.get_best_score())}"
    try:
        stdscr.addnstr(2, max(0, (width - len(score_str)) // 2), score_str, width - 2)
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
            
            pair_id = color_map.get(val, 1)
            attr = curses.color_pair(pair_id) | curses.A_BOLD
            
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
    if game.is_won() and not game.is_over():
        msg = "You reached 2048! Press 'c' to continue, 'q' to quit."
        try:
            stdscr.addnstr(status_y, max(0, (width - len(msg))//2), msg, width - 2, 
                          curses.color_pair(color_map.get(2048, 1)) | curses.A_BOLD)
        except curses.error:
            pass
    elif game.is_over():
        msg = f"Game Over! Score: {format_score(game.get_score())} | 'r': restart, 'q': quit"
        try:
            stdscr.addnstr(status_y, max(0, (width - len(msg))//2), msg, width - 2, 
                          curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

    # Instructions
    instr_y = status_y + 2
    undo_hint = " | 'u': Undo" if game.undo_stack else ""
    instr = f"Arrows/WASD: Move{undo_hint} | 'r': New Game | 'q': Quit"
    try:
        stdscr.addnstr(instr_y, max(0, (width - len(instr))//2), instr, width - 2, curses.A_DIM)
    except curses.error:
        pass

    stdscr.refresh()


def main(stdscr):
    """Main game loop with input handling."""
    curses.curs_set(0)
    
    # Initialize color pairs
    color_map = init_colors()
    
    # Create game instance
    game = Game()
    game.new_game()
    
    while True:
        draw_board(stdscr, game, color_map)
        
        key = stdscr.getch()
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('r') or key == ord('R'):
            game.new_game()
        elif key == ord('c') or key == ord('C'):
            game.continue_after_win = True
            game.won = False
        elif key == ord('u') or key == ord('U'):
            game.undo()
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            game.move("up")
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            game.move("down")
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            game.move("left")
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            game.move("right")
    
    curses.endwin()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
