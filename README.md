# Bloxorz 3D

A minimalist, architectural 3D implementation of the classic Bloxorz puzzle game and solver testbed. Designed with a focus on Swiss typography, a cohesive mineral color palette, tactile procedural audio synthesis, and frame-rate independent physics/animation supporting 60 to 120+ FPS.

The project maintains a strict decoupling between pure Python game logic and the 3D rendering pipeline, providing a clean API for integrating automated solvers and AI search algorithms.

---

### Technical Architecture

```text
bloxorz_solvers/
├── bloxorz/
│   ├── audio/              # Zero-dependency procedural 16-bit WAV synthesizer
│   ├── config.py           # Central configuration loader (TOML / JSON parsing)
│   ├── core/               # Pure Python game logic (Engine-agnostic)
│   │   ├── block.py        # Spatial coordinates, 12 rolling states, occupied cells
│   │   ├── board.py        # Grid structures, bridges, switches, state cloning
│   │   ├── constants.py    # Enums (Direction, BlockOrientation, TileType, GameStatus)
│   │   ├── game.py         # Session management, turn history, and infinite undo
│   │   └── level_loader.py # JSON and ASCII level parser
│   ├── graphics/           # 3D rendering engine (Ursina / Panda3D)
│   │   ├── block_view.py   # Frame-perfect delta-time rotation hierarchy
│   │   ├── board_view.py   # Procedural tile generation and bridge animation
│   │   └── camera_ctrl.py  # Golden-ratio isometric camera positioning
│   ├── levels/             # Packaged stages (All 33 canonical stages: stage_01 to stage_33)
│   │   ├── stage_01.json
│   │   ├── ...
│   │   └── stage_33.json
│   ├── solvers/            # Pluggable solver architecture
│   │   └── base.py         # BaseSolver, SolverResult, and Successor contracts
│   ├── ui/                 # Typography-driven interface system
│   │   ├── hud.py          # Real-time move counter, status banners, hotkeys
│   │   ├── menu.py         # Pause, stage selector, and victory overlays
│   │   └── theme.py        # Central design tokens and motion easing constants
│   └── main.py             # Application coordinator and runtime event loop
├── data/                   # Data archive and ground-truth benchmark suite
│   ├── coolmath.json       # Canonical 33-stage dataset from Coolmath Games
│   ├── solutions.json      # Ground-truth minimal-move solution sequences (1,999 moves total)
│   ├── external_maps/      # 33 raw text maps from phamquiluan/BloxorzSolver
│   └── SOURCES.md          # Upstream repository credits, schemas, and stage catalog
├── tests/                  # Automated verification suite (100% pass)
│   ├── test_config.py      # Configuration parsing and fallback tests
│   ├── test_core.py        # Mathematical verification of rolling and tile mechanics
│   ├── test_input.py       # Arrow key schemes, debouncing, and event listeners
│   ├── test_levels.py      # Schema and ground-truth solution checks across all 33 levels
│   └── test_solvers_base.py# Solver base contract verification
├── config.toml             # Central configuration file (display, camera, physics, audio, controls)
├── CONTRIBUTING.md         # Architecture and contribution guidelines
├── requirements.txt        # Runtime and development dependencies
├── run.py                  # CLI entry point and solver execution launcher
└── pytest.ini              # Test runner configuration
```

---

## Solver Communication Interface

The platform provides a dual-layer communication interface: a high-throughput headless simulation layer for search algorithms and a real-time playback layer for 3D visualization.

### 1. Headless Simulation (Pure Python Logic)

The simulation engine in `bloxorz.core` executes hundreds of thousands of state evaluations per second without launching graphics:

```python
from bloxorz.core.constants import Direction, BlockOrientation, TileType
from bloxorz.core.level_loader import LevelLoader
from bloxorz.core.board import Board
from bloxorz.core.block import BlockState

# Load board geometry
board: Board = LevelLoader.load_json_level("bloxorz/levels/stage_01.json")

# Starting state
block: BlockState = board.spawn_state  # Frozen dataclass (hashable for visited sets)
print(block.x, block.y, block.orientation, block.occupied_cells)

# Compute next step (pure transformation)
next_block = block.roll(Direction.RIGHT)

# Evaluate against board rules
outcome, cause = board.evaluate_block_state(next_block)
# outcome in ("SAFE", "VICTORY", "FELL_VOID", "FELL_FRAGILE")

# State-space exploration utilities
cloned_board = board.clone()
bridge_key = board.get_bridge_state_key()  # Hashable tuple for visited sets
state_signature = (next_block, bridge_key)
```

### 2. Live 3D Playback & Solver Registration

To visualize your custom solver in the 3D application, register a solver callback function via `run.launch()`:

```python
# solver_example.py
from typing import List
from bloxorz.core.constants import Direction
from bloxorz.core.board import Board
from run import launch

def my_solver(board: Board) -> List[Direction]:
    """
    Custom search algorithm implementation.
  
    Args:
        board: The active stage Board instance.
    
    Returns:
        List of Direction moves to reach the goal.
    """
    # Your search algorithm here (BFS, DFS, A*, etc.)
    return [
        Direction.RIGHT, Direction.RIGHT, Direction.DOWN, Direction.DOWN,
        Direction.RIGHT, Direction.UP, Direction.RIGHT, Direction.RIGHT
    ]

if __name__ == "__main__":
    launch(solver=my_solver)
```

Press **`[ P ]`** during gameplay to execute the registered solver. The game will automatically play through the solution with smooth 3D rotations, tile interactions, and sound effects.

### 3. Programmatic Step & State Query API

For reinforcement learning agents or external controllers:

```python
# Query current runtime state snapshot
state = app.get_state()
# Returns: {
#   "stage_index": int,
#   "stage_name": str,
#   "block": BlockState,
#   "board": Board,
#   "move_count": int,
#   "status": GameStatus,
#   "is_animating": bool,
#   "is_playing_solution": bool
# }

# Execute single step
app.step(Direction.UP, on_done=lambda outcome: print("Result:", outcome))
```

---

## Installation & Setup

### Requirements

- Python 3.10 or higher (compatible with Python 3.10 through 3.14)
- Linux (X11 / Wayland) or Windows 10/11

### 1. Environment Configuration

```bash
# Clone the repository
git clone https://github.com/username/boxorz_solvers.git
cd boxorz_solvers

# Initialize virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Launching the Application

```bash
# Launch interactive 3D game
python run.py
```

### 3. Running Verification Suites

```bash
# Run automated test suite
pytest tests/ -v

# Run PEP 8 compliance checks
flake8 bloxorz/ tests/ --max-line-length=120
```

---

## Controls

| Key                     | Action                                   |
| :---------------------- | :--------------------------------------- |
| `W` / `Up Arrow`    | Roll Northeast (+X axis)                 |
| `S` / `Down Arrow`  | Roll Southwest (-X axis)                 |
| `A` / `Left Arrow`  | Roll Northwest (-Y axis)                 |
| `D` / `Right Arrow` | Roll Southeast (+Y axis)                 |
| `U`                   | Undo last move (infinite history)        |
| `R`                   | Restart current stage                    |
| `P`                   | Execute registered solver                |
| `M`                   | Toggle procedural audio mute             |
| `ESC`                 | Open / close Pause and Stage Select menu |
| `SPACE`               | Advance to next stage upon victory       |

---

## Code Quality Standards

- **PEP 8 Compliance**: Strict line length and style adherence verified via Flake8.
- **Type Annotations**: Comprehensive type hints across all core and rendering modules.
- **Zero Asset Dependencies**: Audio waveforms are synthesized algorithmically in memory; 3D models are generated procedurally at runtime.
- **State Determinism**: Core game state transitions are fully deterministic and free of frame-rate artifacts.
