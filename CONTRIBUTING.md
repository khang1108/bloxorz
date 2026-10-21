# Contributing Guidelines

Thank you for contributing to Bloxorz 3D. To preserve the project's architectural integrity, minimalist aesthetics, and rigorous software engineering standards, all contributors must adhere to the following principles, conventions, and guidelines.

---

## 1. Architectural Principles

### 1.1 Strict Decoupling of Core Logic and Rendering
The repository enforces a strict boundary between the computational game logic and the 3D visual engine:
- **`bloxorz.core`** must remain completely engine-agnostic. Under no circumstances should modules in `bloxorz.core` import `ursina`, `panda3d`, or any rendering/audio libraries. All state mutations must be pure, deterministic, and runnable in headless environments.
- **`bloxorz.graphics`** operates as a passive observer and interpolator of state. Graphics entities receive state transitions from `Game` or `BlockState` and apply delta-time easing and transformations.
- **`bloxorz.audio`** generates sound procedurally in memory via mathematical waveforms. Do not introduce static external audio assets (`.mp3`, `.wav`, `.ogg`) into the repository.
- **`bloxorz.ui`** follows a typography-driven design language. Icon fonts and ad-hoc visual glyphs are prohibited. All colors, font sizes, and transition timings must reference tokens defined in `bloxorz.ui.theme.Theme`.

### 1.2 Immutability and State Search Readiness
State representations used in search trees (such as `BlockState`) must remain immutable (`@dataclass(frozen=True)`) to allow direct usage in hashed collections (`set`, `dict`).
Dynamic mutable entities (such as `Board`) must provide deterministic `.clone()` and `.reset()` implementations.

---

## 2. Coding Standards & Conventions

### 2.1 Python Specification
- Target Python 3.10+ (tested through Python 3.14).
- Avoid deprecated standard library features and platform-specific POSIX/Windows-only constructs. File paths must utilize `pathlib.Path`.

### 2.2 Style and Formatting (PEP 8)
- **Line Length**: Maximum 120 characters per line.
- **Linter**: Code must pass `flake8` verification with zero warnings:
  ```bash
  flake8 bloxorz/ tests/ --max-line-length=120
  ```
- **Imports**: Group imports according to PEP 8:
  1. Standard library imports
  2. Third-party library imports (e.g., `ursina`, `pytest`)
  3. Local application imports (e.g., `bloxorz.core.constants`)
- **Naming Conventions**:
  - Modules and packages: `snake_case` (e.g., `level_loader.py`)
  - Classes and Exception types: `PascalCase` (e.g., `BlockState`, `BoardView`)
  - Functions and methods: `snake_case` (e.g., `evaluate_block_state()`)
  - Constants and Enum members: `UPPER_SNAKE_CASE` (e.g., `BlockOrientation.LYING_X`)
  - Internal or private attributes: Prefix with a single underscore `_` (e.g., `self._is_animating`)

### 2.3 Type Annotations
All functions, methods, and class attributes must provide explicit type hints:
```python
def evaluate_block_state(self, block: BlockState) -> Tuple[str, Optional[Tuple[int, int]]]:
    ...
```

### 2.4 Documentation & Comments
- Public classes and non-trivial methods require docstrings explaining inputs, return types, and side effects.
- Explain non-obvious geometric or mathematical transformations (e.g., 3D pivot coordinate rotation mathematics).
- Preserve existing comments and docstrings across modified files.

---

## 3. Testing Requirements

All contributions that introduce new features, level formats, or bug fixes must include corresponding automated tests.

### 3.1 Unit Testing (`pytest`)
- Run the full test suite before committing:
  ```bash
  pytest tests/ -v
  ```
- Tests must execute in headless mode without requiring a graphical window or display server.
- Coverage expectations:
  - Any new method added to `bloxorz.core` must have explicit test cases in `tests/test_core.py`.
  - Any new level added to `bloxorz/levels/` must validate successfully against schema and reachability checks in `tests/test_levels.py`.

---

## 4. Development Workflow

### 4.1 Branching Strategy
- `main`: Production-ready, stable codebase.
- Feature branches: `feat/<feature-name>` (e.g., `feat/a-star-solver`, `feat/stage-editor`).
- Bugfix branches: `fix/<issue-name>` (e.g., `fix/pivot-rotation-jitter`).

### 4.2 Commit Messages
Use the Conventional Commits specification:
- `feat`: A new feature (e.g., `feat(core): add heuristic distance utility to Board`)
- `fix`: A bug fix (e.g., `fix(graphics): resolve pivot offset on stage reset`)
- `refactor`: Code restructuring without functional changes (e.g., `refactor(ui): extract hud tokens`)
- `test`: Adding or updating test cases (e.g., `test(core): add fragile tile collapse tests`)
- `docs`: Documentation updates (e.g., `docs: update solver communication guide`)
- `chore`: Maintenance tasks, dependencies, or configuration changes

---

## 5. Pull Request Checklist

Before submitting a Pull Request, verify:
- [ ] Code passes all tests via `pytest tests/`.
- [ ] Code conforms to style guidelines via `flake8 bloxorz/ tests/ --max-line-length=120`.
- [ ] New logic is covered by unit tests.
- [ ] No third-party rendering or audio dependencies are introduced into `bloxorz.core`.
- [ ] No external asset files (`.png`, `.wav`, `.obj`) have been added; assets must remain procedurally generated.
- [ ] Documentation (`README.md`, `CONTRIBUTION.md`) has been updated where relevant.
