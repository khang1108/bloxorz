from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from ursina import (
    Ursina,
    Entity,
    window,
    color,
    invoke,
)

from bloxorz.core.constants import Direction, GameStatus
from bloxorz.core.board import Board
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.ui.theme import Palette
from bloxorz.ui.hud import HUD
from bloxorz.ui.menu import MenuManager
from bloxorz.graphics.camera_ctrl import CameraController
from bloxorz.graphics.board_view import BoardView
from bloxorz.graphics.block_view import BlockView
from bloxorz.audio.sound_manager import SoundManager


class BloxorzApp:
    """Master application coordinator managing graphics, input, audio, and state."""

    def __init__(self):
        # Configure Ursina window for high refresh-rate minimalist experience
        window.title = "BLOXORZ 3D  ·  ARCHITECTURAL MINIMALISM"
        window.borderless = False
        window.fullscreen = False
        window.size = (1280, 720)
        window.color = color.hex(Palette.BACKGROUND.hex_code)
        window.show_ursina_splash = False
        window.vsync = True  # Supports 60, 120, 144+ FPS without screen tearing

        # Find level files
        self.levels_dir = Path(__file__).parent / "levels"
        self.stage_files = sorted(self.levels_dir.glob("stage_*.json"))
        self.current_stage_idx: int = 1

        # Instantiate subsystems
        self.sound_mgr = SoundManager()
        self.sound_mgr.load_audio_objects()

        self.camera_ctrl = CameraController()
        self.board_view = BoardView()
        self.block_view = BlockView()
        self.hud = HUD()

        # Solver & programmatic automation interface
        self.registered_solver: Optional[Callable[[Board], List[Direction]]] = None
        self._is_playing_solution: bool = False
        self._active_solution: List[Direction] = []
        self._solution_idx: int = 0
        self._solution_delay: float = 0.08
        self._on_solution_complete: Optional[Callable[[], None]] = None

        self.menu_mgr = MenuManager(
            on_resume=self.resume_game,
            on_restart=self.restart_stage,
            on_select_stage=self.load_stage_by_index,
            on_next_stage=self.next_stage,
            on_toggle_audio=self.sound_mgr.toggle_audio,
            get_audio_status=lambda: self.sound_mgr.enabled,
            stages_count=len(self.stage_files),
        )

        self.game: Game = None
        self.load_stage_by_index(self.current_stage_idx, animate_camera=False)

    def load_stage_by_index(self, stage_idx: int, animate_camera: bool = True):
        """Loads and initializes a stage by 1-based index."""
        if not (1 <= stage_idx <= len(self.stage_files)):
            stage_idx = 1
        self.current_stage_idx = stage_idx

        stage_file = self.stage_files[stage_idx - 1]
        board = load_level_from_file(stage_file)
        self.game = Game(board)

        # Build visuals
        self.board_view.build(board)
        self.block_view.sync_to_state(board.spawn_state)
        self.camera_ctrl.frame_board(board.min_x, board.max_x, board.min_y, board.max_y, animate=animate_camera)

        # Update HUD
        self.hud.update_stage(board.level_name, f"STAGE {stage_idx:02d} / {len(self.stage_files):02d}")
        self.hud.update_moves(0)
        self.hud.hide_banner()
        self.menu_mgr.close_all()

    def restart_stage(self):
        """Resets the current stage."""
        if self.game:
            self.game.restart()
            self.board_view.update_bridges(self.game.board)
            self.block_view.sync_to_state(self.game.board.spawn_state)
            self.hud.update_moves(0)
            self.hud.hide_banner()
            self.menu_mgr.close_all()

    def resume_game(self):
        """Closes pause menu and returns to play."""
        self.menu_mgr.close_all()

    def next_stage(self):
        """Advances to the next stage or loops to beginning."""
        next_idx = self.current_stage_idx + 1
        if next_idx > len(self.stage_files):
            next_idx = 1
        self.load_stage_by_index(next_idx)

    def handle_undo(self):
        """Performs turn undo."""
        if self.block_view.is_animating or not self.game:
            return
        if self.game.undo():
            self.sound_mgr.play("undo")
            self.block_view.sync_to_state(self.game.block)
            self.board_view.update_bridges(self.game.board)
            self.hud.update_moves(self.game.move_count)
            self.hud.hide_banner()

    def handle_move(self, direction: Direction, on_done: Optional[Callable[[str], None]] = None):
        """Executes a move request from player input or solver API."""
        if not self.game or self.block_view.is_animating or self.game.status != GameStatus.PLAYING:
            if on_done:
                on_done("IGNORED")
            return

        prev_state = self.game.block
        outcome, next_state, detail = self.game.roll(direction)

        if outcome == "IGNORED":
            if on_done:
                on_done("IGNORED")
            return

        self.sound_mgr.play("roll")

        def on_roll_finished():
            if outcome == "SAFE":
                self.hud.update_moves(self.game.move_count)
                if detail:  # Toggled bridges
                    self.sound_mgr.play("switch")
                    self.board_view.update_bridges(self.game.board)
                    # Trigger switch plate depression
                    for cell in next_state.occupied_cells:
                        self.board_view.animate_switch_press(cell[0], cell[1])

            elif outcome == "VICTORY":
                self.hud.update_moves(self.game.move_count)
                self.sound_mgr.play("win")
                self.block_view.animate_victory(
                    on_complete=lambda: self.menu_mgr.show_victory_menu(
                        self.game.board.level_name, self.game.move_count
                    )
                )

            elif outcome in ("FELL_VOID", "FELL_FRAGILE", "FELL_HALF_GOAL"):
                self.hud.update_moves(self.game.move_count)
                self.sound_mgr.play("fall")
                banner_msg = "FRAGILE COLLAPSE" if outcome == "FELL_FRAGILE" else "FELL INTO VOID"
                self.hud.show_banner(banner_msg)

                def on_fall_done():
                    invoke(self.restart_stage, delay=0.2)

                self.block_view.animate_fall(on_complete=on_fall_done)

            if on_done:
                on_done(outcome)

        self.block_view.roll_animated(prev_state, next_state, direction, on_complete=on_roll_finished)

    # =========================================================================
    # SOLVER COMMUNICATION & AUTOMATION API
    # =========================================================================

    def register_solver(self, solver_callback: Callable[[Board], List[Direction]]):
        """Registers a user solver function: solver_fn(board) -> List[Direction]."""
        self.registered_solver = solver_callback

    def trigger_solver(self):
        """Executes the registered solver on the current stage and animates the solution."""
        if not self.registered_solver or not self.game:
            return
        if self.block_view.is_animating or self._is_playing_solution:
            return

        moves = self.registered_solver(self.game.board)
        if moves:
            self.hud.show_banner(f"SOLVER: {len(moves)} MOVES")
            invoke(self.hud.hide_banner, delay=1.2)
            self.play_solution(moves)

    def play_solution(
        self,
        moves: List[Direction],
        delay_between_moves: float = 0.08,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """Sequentially executes a list of directions from a solver with 3D animation."""
        if not moves:
            return
        self._active_solution = list(moves)
        self._solution_idx = 0
        self._solution_delay = delay_between_moves
        self._on_solution_complete = on_complete
        self._is_playing_solution = True
        self._play_next_solver_step()

    def _play_next_solver_step(self):
        """Plays the next queued step in the solver solution."""
        if not self._is_playing_solution:
            return
        if self._solution_idx >= len(self._active_solution):
            self._is_playing_solution = False
            if self._on_solution_complete:
                self._on_solution_complete()
            return

        next_dir = self._active_solution[self._solution_idx]
        self._solution_idx += 1

        def on_step_finished(outcome: str):
            if outcome == "SAFE":
                invoke(self._play_next_solver_step, delay=self._solution_delay)
            elif outcome == "VICTORY":
                self._is_playing_solution = False
                if self._on_solution_complete:
                    self._on_solution_complete()
            else:
                self._is_playing_solution = False

        self.handle_move(next_dir, on_done=on_step_finished)

    def stop_solution(self):
        """Stops ongoing solver solution playback."""
        self._is_playing_solution = False
        self._active_solution.clear()

    def step(self, direction: Direction, on_done: Optional[Callable[[str], None]] = None):
        """Programmatic single move execution for external solvers and AI agents."""
        self.handle_move(direction, on_done=on_done)

    def get_state(self) -> Dict[str, Any]:
        """Returns a comprehensive state snapshot for external solvers and agents."""
        if not self.game:
            return {}
        return {
            "stage_index": self.current_stage_idx,
            "stage_name": self.game.board.level_name,
            "block": self.game.block,
            "board": self.game.board,
            "move_count": self.game.move_count,
            "status": self.game.status,
            "is_animating": self.block_view.is_animating,
            "is_playing_solution": self._is_playing_solution,
        }

    # =========================================================================
    # USER KEYBOARD INPUT
    # =========================================================================

    def handle_input(self, key: str):
        """Processes global keyboard shortcuts."""
        k = key.lower()

        # Movement: W-S swapped with A-D to align with isometric projection + full arrow keys support
        if k in ("w", "arrow_up", "up arrow", "up"):
            self.handle_move(Direction.RIGHT)
        elif k in ("s", "arrow_down", "down arrow", "down"):
            self.handle_move(Direction.LEFT)
        elif k in ("a", "arrow_left", "left arrow", "left"):
            self.handle_move(Direction.UP)
        elif k in ("d", "arrow_right", "right arrow", "right"):
            self.handle_move(Direction.DOWN)

        # Actions
        elif k == "u":
            self.handle_undo()
        elif k == "r":
            self.restart_stage()
        elif k == "m":
            self.sound_mgr.toggle_audio()
        elif k == "p":
            self.trigger_solver()
        elif k == "escape":
            if self.menu_mgr.pause_root or self.menu_mgr.stage_select_root:
                self.menu_mgr.close_all()
            else:
                self.menu_mgr.show_pause_menu()
        elif k == "space":
            if self.menu_mgr.victory_root:
                self.next_stage()


class InputHandler(Entity):
    """OOP Input dispatching entity for Ursina event loop."""

    def __init__(self, app_instance: BloxorzApp):
        super().__init__()
        self.app_instance = app_instance

    def input(self, key):
        self.app_instance.handle_input(key)


def main():
    """Application launcher."""
    app = Ursina()
    bloxorz = BloxorzApp()
    _ = InputHandler(bloxorz)
    app.run()


if __name__ == "__main__":
    main()
