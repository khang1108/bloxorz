import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from ursina import (
    Ursina,
    Entity,
    window,
    color,
    invoke,
    camera,
)

from bloxorz.core.constants import Direction, GameStatus
from bloxorz.core.board import Board
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.solvers.base import SolverAction, SWITCH_ACTION
from bloxorz.ui.theme import Palette
from bloxorz.ui.hud import HUD
from bloxorz.ui.menu import MenuManager
from bloxorz.ui.solver_widget import SolverWidget
from bloxorz.solvers import get_solver
from bloxorz.graphics.camera_ctrl import CameraController
from bloxorz.graphics.board_view import BoardView
from bloxorz.graphics.block_view import BlockView
from bloxorz.audio.sound_manager import SoundManager
from bloxorz.config import CONFIG


class BloxorzApp:
    """Master application coordinator managing graphics, input, audio, and state."""

    def __init__(self):
        # Configure Ursina window from centralized config
        window.title = CONFIG.window.title
        window.borderless = CONFIG.window.borderless
        window.fullscreen = CONFIG.window.fullscreen
        window.size = (CONFIG.window.width, CONFIG.window.height)
        window.color = color.hex(Palette.BACKGROUND.hex_code)
        window.show_ursina_splash = False
        window.vsync = CONFIG.window.vsync

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
        self.registered_solver: Optional[Callable[[Board], List[SolverAction]]] = None
        self._is_playing_solution: bool = False
        self._active_solution: List[SolverAction] = []
        self._solution_idx: int = 0
        self._solution_delay: float = CONFIG.solver.default_delay
        self._on_solution_complete: Optional[Callable[[], None]] = None
        self._solution_generation: int = 0
        self.active_solver_name: str = "BFS"
        self.set_active_solver("BFS")

        ui_parent = None
        try:
            ui_parent = camera.ui
        except Exception:
            ui_parent = None

        self.solver_widget = SolverWidget(
            parent=ui_parent,
            on_select_algorithm=self.set_active_solver,
            on_run_solver=self.toggle_solver,
            initial_algorithm=self.active_solver_name,
        )

        self.menu_mgr = MenuManager(
            on_resume=self.resume_game,
            on_restart=self.restart_stage,
            on_select_stage=self.load_stage_by_index,
            on_next_stage=self.next_stage,
            on_toggle_audio=self.sound_mgr.toggle_audio,
            get_audio_status=lambda: self.sound_mgr.enabled,
            stages_count=len(self.stage_files),
            sound_mgr=self.sound_mgr,
        )

        self.game: Game = None
        self._last_input_time: float = 0.0
        self._last_input_key: str = ""
        self.input_handler = InputHandler(self)
        self.load_stage_by_index(self.current_stage_idx, animate_camera=False)

    def load_stage_by_index(self, stage_idx: int, animate_camera: bool = True):
        """Loads and initializes a stage by 1-based index."""
        self.stop_solution()
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
        self.hud.set_split_mode(getattr(self.game.block, "is_split", False))
        self.menu_mgr.close_all()
        if getattr(self, "solver_widget", None):
            self.solver_widget.set_running_state(False)
            self.solver_widget.set_visible(True)

    def restart_stage(self, show_banner: bool = True):
        """Resets the current stage."""
        self.stop_solution()
        if getattr(self, "solver_widget", None):
            self.solver_widget.set_visible(True)
        if self.game:
            if hasattr(self, "sound_mgr") and self.sound_mgr and show_banner:
                self.sound_mgr.play("restart")
            self.game.restart()
            if getattr(self, "board_view", None) and hasattr(self.board_view, "update_bridges"):
                self.board_view.update_bridges(self.game.board)
            if getattr(self, "block_view", None) and hasattr(self.block_view, "sync_to_state"):
                self.block_view.sync_to_state(self.game.board.spawn_state)
            if getattr(self, "hud", None):
                if hasattr(self.hud, "update_moves"):
                    self.hud.update_moves(0)
                if hasattr(self.hud, "set_split_mode"):
                    self.hud.set_split_mode(getattr(self.game.block, "is_split", False))
                if show_banner and hasattr(self.hud, "show_banner"):
                    self.hud.show_banner("Argghhh let's try again", duration=2.5)
                elif hasattr(self.hud, "hide_banner"):
                    self.hud.hide_banner()
            if getattr(self, "menu_mgr", None) and hasattr(self.menu_mgr, "close_all"):
                self.menu_mgr.close_all()
            if getattr(self, "camera_ctrl", None):
                if hasattr(self.camera_ctrl, "reset_view"):
                    self.camera_ctrl.reset_view(animate=True)
                self.camera_ctrl.enabled_controls = True

    def resume_game(self):
        """Closes pause menu and returns to play."""
        self.menu_mgr.close_all()
        self.camera_ctrl.enabled_controls = True
        if getattr(self, "solver_widget", None):
            self.solver_widget.set_visible(True)

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
            self.hud.set_split_mode(getattr(self.game.block, "is_split", False))

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
            if outcome in ("SAFE", "MERGED", "TELEPORT"):
                self.hud.update_moves(self.game.move_count)
                self.hud.set_split_mode(getattr(self.game.block, "is_split", False))
                if outcome == "TELEPORT":
                    self.sound_mgr.play("switch")
                    self.hud.show_banner("TELEPORT SPLIT")
                elif outcome == "MERGED":
                    self.sound_mgr.play("merge")
                    self.hud.show_banner("BLOCKS MERGED")

                if detail and outcome in ("SAFE", "MERGED"):  # Toggled bridges
                    self.sound_mgr.play("switch")
                    self.board_view.update_bridges(self.game.board)
                    # Trigger switch plate depression
                    for cell in next_state.occupied_cells:
                        self.board_view.animate_switch_press(cell[0], cell[1])

            elif outcome == "VICTORY":
                self.hud.update_moves(self.game.move_count)
                self.sound_mgr.play("win")
                gx, gy = self.game.board.goal_pos
                self.camera_ctrl.animate_victory_focus(gx, gy)

                def on_victory_done():
                    if getattr(self, "solver_widget", None):
                        self.solver_widget.set_visible(False)
                        self.solver_widget.set_running_state(False)
                    self.menu_mgr.show_victory_menu(
                        self.game.board.level_name, self.game.move_count, self.current_stage_idx
                    )

                self.block_view.animate_victory(on_complete=on_victory_done)

            elif outcome in ("FELL_VOID", "FELL_FRAGILE"):
                self.hud.update_moves(self.game.move_count)
                self.sound_mgr.play("fall")
                banner_msg = "FRAGILE COLLAPSE" if outcome == "FELL_FRAGILE" else "FELL INTO VOID"
                self.hud.show_banner(banner_msg)

                def on_fall_done():
                    invoke(self.restart_stage, delay=0.2)

                self.block_view.animate_fall(
                    board=self.game.board,
                    direction=direction,
                    on_complete=on_fall_done,
                )

            if on_done:
                on_done(outcome)

        self.block_view.roll_animated(
            prev_state,
            next_state,
            direction,
            on_complete=on_roll_finished,
            on_split_takeoff=lambda: self.sound_mgr.play("switch"),
        )

    # =========================================================================
    # SOLVER COMMUNICATION & AUTOMATION API
    # =========================================================================

    def register_solver(self, solver_callback: Callable[[Board], List[SolverAction]]):
        """Register a callback returning Direction moves and optional SWITCH actions."""
        self.registered_solver = solver_callback

    def set_active_solver(self, algo_name: str):
        """Switches the active search solver algorithm (BFS, DFS, UCS, A*)."""
        self.active_solver_name = algo_name.upper().strip()
        solver_instance = get_solver(self.active_solver_name)
        self.register_solver(solver_instance)
        if getattr(self, "solver_widget", None) and self.solver_widget.current_algorithm != self.active_solver_name:
            self.solver_widget.select_algorithm(self.active_solver_name)

    def toggle_solver(self):
        """Starts or aborts solver execution."""
        if self._is_playing_solution:
            self.stop_solution()
        else:
            self.trigger_solver()

    def trigger_solver(self) -> None:
        """Solve from a fresh stage, reporting missing solvers and empty results."""
        if not self.game:
            return
        if self.block_view.is_animating or self._is_playing_solution:
            return

        algo = getattr(self, "active_solver_name", "")
        if algo in ("DFS", "A*"):
            self.hud.show_banner(f"{algo}: COMING SOON", duration=1.5)
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)
            return

        if self.registered_solver is None:
            self.hud.show_banner("NO SOLVER REGISTERED")
            return

        # The callback accepts a Board and solves from spawn, not the current block.
        self.restart_stage(show_banner=False)
        try:
            moves = self.registered_solver(self.game.board)
        except NotImplementedError:
            self.hud.show_banner("SOLVER DOES NOT SUPPORT THIS STAGE")
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)
            return
        except ValueError:
            self.hud.show_banner("SOLVER ERROR")
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)
            return
        if moves:
            move_count = sum(isinstance(action, Direction) for action in moves)
            self.hud.show_banner(f"SOLVER: {move_count} MOVES", duration=1.2)
            self.play_solution(moves)
        elif self.game.board.evaluate_block_state(self.game.block)[0] == "VICTORY":
            self.hud.show_banner("ALREADY AT GOAL")
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)
        else:
            self.hud.show_banner("SOLVER FOUND NO SOLUTION")
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)

    def play_solution(
        self,
        moves: List[SolverAction],
        delay_between_moves: float = 0.08,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """Sequentially executes a list of directions from a solver with 3D animation."""
        if not moves:
            return
        self.stop_solution()
        self._active_solution = list(moves)
        self._solution_idx = 0
        self._solution_delay = delay_between_moves
        self._on_solution_complete = on_complete
        self._is_playing_solution = True
        if getattr(self, "solver_widget", None):
            self.solver_widget.set_running_state(True)
        self._play_next_solver_step(generation=self._solution_generation)

    def _play_next_solver_step(self, generation: Optional[int] = None) -> None:
        """Plays the next queued step in the solver solution."""
        if generation is not None and generation != self._solution_generation:
            return
        if not self._is_playing_solution:
            return
        if self._solution_idx >= len(self._active_solution):
            self._is_playing_solution = False
            if getattr(self, "solver_widget", None):
                self.solver_widget.set_running_state(False)
            if self._on_solution_complete:
                self._on_solution_complete()
            return

        next_dir = self._active_solution[self._solution_idx]
        self._solution_idx += 1
        current_generation = self._solution_generation

        if next_dir is None or next_dir == SWITCH_ACTION or next_dir == "_":
            if getattr(self.game.block, "is_split", False):
                self.game.switch_block()
                self.sound_mgr.play("switch")
                self.block_view.sync_to_state(self.game.block)
            invoke(self._play_next_solver_step, current_generation, delay=self._solution_delay)
            return

        def on_step_finished(outcome: str):
            if current_generation != self._solution_generation or not self._is_playing_solution:
                return
            if outcome in ("SAFE", "MERGED", "TELEPORT"):
                invoke(self._play_next_solver_step, current_generation, delay=self._solution_delay)
            elif outcome == "VICTORY":
                self._is_playing_solution = False
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_running_state(False)
                if self._on_solution_complete:
                    self._on_solution_complete()
            else:
                self._is_playing_solution = False
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_running_state(False)

        self.handle_move(next_dir, on_done=on_step_finished)

    def stop_solution(self) -> None:
        """Stop playback and invalidate callbacks queued before a stage reset."""
        self._solution_generation += 1
        self._is_playing_solution = False
        self._active_solution.clear()
        self._solution_idx = 0
        self._on_solution_complete = None
        if getattr(self, "solver_widget", None):
            self.solver_widget.set_running_state(False)

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
        """Processes global keyboard shortcuts with robust normalization and debouncing."""
        k = key.lower().strip()
        k_clean = k.replace("-", "_").replace(" ", "_")
        if k_clean.startswith("raw_"):
            k_clean = k_clean[4:]

        # Debounce duplicate events arriving within 50ms (scroll has 10ms window)
        now = time.time()
        is_scroll = k_clean in ("scroll_up", "scroll_down", "wheel_up", "wheel_down")
        debounce_window = 0.01 if is_scroll else 0.05
        if (
            k_clean == getattr(self, "_last_input_key", "")
            and (now - getattr(self, "_last_input_time", 0.0)) < debounce_window
        ):
            return
        self._last_input_time = now
        self._last_input_key = k_clean

        # Camera Controls (Zoom, Orbit, Reset)
        if k_clean in ("scroll_up", "wheel_up", "page_up", "+", "="):
            self.camera_ctrl.zoom(-1.0)
            return
        if k_clean in ("scroll_down", "wheel_down", "page_down", "-", "_"):
            self.camera_ctrl.zoom(1.0)
            return
        if k_clean == "q":
            self.camera_ctrl.step_orbit(-1)
            return
        if k_clean == "e":
            self.camera_ctrl.step_orbit(1)
            return
        if k_clean == "c":
            self.camera_ctrl.reset_view()
            return

        # Global Control Actions
        if k_clean == "u":
            self.handle_undo()
            return
        if k_clean == "r":
            self.restart_stage()
            return
        if k_clean == "m":
            self.sound_mgr.toggle_audio()
            return
        if k_clean in ("o", "raw_o"):
            if self.menu_mgr.is_settings_open():
                self.menu_mgr.close_all()
                self.camera_ctrl.enabled_controls = True
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_visible(True)
            else:
                self.camera_ctrl.enabled_controls = False
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_visible(False)
                self.menu_mgr.show_settings_menu(self.current_stage_idx)
            return
        if k_clean == "p":
            self.trigger_solver()
            return
        if k_clean == "escape":
            if self.menu_mgr.is_any_menu_open():
                self.menu_mgr.close_all()
                self.camera_ctrl.enabled_controls = True
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_visible(True)
            else:
                self.camera_ctrl.enabled_controls = False
                if getattr(self, "solver_widget", None):
                    self.solver_widget.set_visible(False)
                self.menu_mgr.show_stage_select_menu(self.current_stage_idx)
            return

        if k_clean == "space":
            if self.menu_mgr.victory_root:
                self.next_stage()
            elif getattr(self.game.block, "is_split", False):
                if not self.block_view.is_animating:
                    switched = self.game.switch_block()
                    if switched:
                        self.sound_mgr.play("switch")
                        self.block_view.sync_to_state(self.game.block)
            return

        arrow_scheme = getattr(getattr(CONFIG, "controls", None), "arrow_scheme", "isometric")

        if arrow_scheme == "classic":
            # Arrow Keys: Classic Bloxorz cardinal grid navigation
            # Right Arrow: East (+X), Left Arrow: West (-X), Up Arrow: North (-Y), Down Arrow: South (+Y)
            if k_clean in ("right_arrow", "arrow_right", "raw_arrow_right", "right"):
                self.handle_move(Direction.RIGHT)
            elif k_clean in ("left_arrow", "arrow_left", "raw_arrow_left", "left"):
                self.handle_move(Direction.LEFT)
            elif k_clean in ("up_arrow", "arrow_up", "raw_arrow_up", "up"):
                self.handle_move(Direction.UP)
            elif k_clean in ("down_arrow", "arrow_down", "raw_arrow_down", "down"):
                self.handle_move(Direction.DOWN)

            # WASD: Screen-relative isometric projection diagonals
            elif k_clean == "w":
                self.handle_move(Direction.RIGHT)  # Screen Up-Right (+X)
            elif k_clean == "s":
                self.handle_move(Direction.LEFT)   # Screen Down-Left (-X)
            elif k_clean == "a":
                self.handle_move(Direction.UP)     # Screen Up-Left (-Y)
            elif k_clean == "d":
                self.handle_move(Direction.DOWN)   # Screen Down-Right (+Y)
        else:
            # Unified Isometric scheme: Both WASD and Arrows steer along screen diagonals
            if k_clean in ("w", "up", "arrow_up", "up_arrow", "raw_arrow_up", "raw_up"):
                self.handle_move(Direction.RIGHT)
            elif k_clean in ("s", "down", "arrow_down", "down_arrow", "raw_arrow_down", "raw_down"):
                self.handle_move(Direction.LEFT)
            elif k_clean in ("a", "left", "arrow_left", "left_arrow", "raw_arrow_left", "raw_left"):
                self.handle_move(Direction.UP)
            elif k_clean in ("d", "right", "arrow_right", "right_arrow", "raw_arrow_right", "raw_right"):
                self.handle_move(Direction.DOWN)


class InputHandler(Entity):
    """OOP Input dispatching entity bridging Ursina event loop and direct Panda3D ShowBase."""

    def __init__(self, app_instance: BloxorzApp):
        super().__init__()
        self.app_instance = app_instance
        self._setup_direct_listeners()

    def _setup_direct_listeners(self):
        """Registers direct ShowBase event listeners for hardware key scancodes.

        On Linux (Wayland/X11/IBus), Ursina only binds 'raw-' listeners for
        alphanumeric keys, ignoring raw control keys ('raw-escape', 'raw-space')
        and raw arrow key scancodes ('raw-arrow_up', etc.).
        Hooking directly into Panda3D ShowBase ensures 100% reliable hardware key delivery.
        """
        try:
            from direct.showbase.ShowBaseGlobal import base
            if not base:
                return

            event_map = {
                "up arrow": ["arrow_up", "raw-arrow_up", "up", "raw-up", "arrow-up", "raw-arrow-up"],
                "down arrow": ["arrow_down", "raw-arrow_down", "down", "raw-down", "arrow-down", "raw-arrow-down"],
                "left arrow": ["arrow_left", "raw-arrow_left", "left", "raw-left", "arrow-left", "raw-arrow-left"],
                "right arrow": [
                    "arrow_right", "raw-arrow_right", "right", "raw-right", "arrow-right", "raw-arrow-right"
                ],
                "escape": ["escape", "raw-escape"],
                "space": ["space", "raw-space"],
                "u": ["u", "raw-u"],
                "r": ["r", "raw-r"],
                "m": ["m", "raw-m"],
                "o": ["o", "raw-o", "raw_o"],
                "p": ["p", "raw-p"],
                "c": ["c", "raw-c"],
                "q": ["q", "raw-q"],
                "e": ["e", "raw-e"],
                "scroll up": ["wheel_up", "raw-wheel_up", "scroll_up", "scroll up"],
                "scroll down": ["wheel_down", "raw-wheel_down", "scroll_down", "scroll down"],
                "+": ["+", "raw-+", "=", "raw-="],
                "-": ["-", "raw--", "_", "raw-_"],
                "w": ["w", "raw-w"],
                "a": ["a", "raw-a"],
                "s": ["s", "raw-s"],
                "d": ["d", "raw-d"],
            }

            for key_name, events in event_map.items():
                for ev in events:
                    base.accept(ev, self._make_event_callback(key_name))
        except Exception:
            pass

    def _make_event_callback(self, key_name: str):
        return lambda: self.app_instance.handle_input(key_name)

    def input(self, key: str):
        self.app_instance.handle_input(key)


def main() -> None:
    """Application launcher."""
    from bloxorz.solvers import UCSSolver

    app = Ursina()
    bloxorz = BloxorzApp()
    bloxorz.register_solver(UCSSolver())
    app.run()


if __name__ == "__main__":
    main()
