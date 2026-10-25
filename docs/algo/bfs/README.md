# Breadth-First Search (BFS) for Bloxorz

The BFS solver explores reachable game states in nondecreasing order of the
number of actions taken. A roll costs one action, and switching control between
split cubes also costs one action. Therefore, the first goal state dequeued is a
shortest solution in solver actions, assuming the state representation and
transitions capture the game rules.

The implementation is in [`bloxorz/solvers/bfs.py`](../../../bloxorz/solvers/bfs.py).
It uses the shared `Game` and `Board` logic to simulate moves, switches,
teleports, and merges rather than duplicating those rules in the search.

## Search problem formulation

### State representation

A search state is the current block state and the current bridge configuration:

```text
state = (block_state, bridge_configuration)
```

The immutable block state has one of two forms:

- **Normal block:** anchor coordinates `(x, y)` and orientation:
  - `STANDING` occupies `(x, y)`.
  - `LYING_X` occupies `(x, y)` and `(x + 1, y)`.
  - `LYING_Y` occupies `(x, y)` and `(x, y + 1)`.
- **Split block:** the two cube coordinates and the active cube index. The
  active cube is the one moved by directional actions; the other stays in
  place. Its canonical key sorts the cube coordinates while retaining the
  active cube's coordinate, so equivalent cube labeling does not create
  duplicate states.

The bridge configuration is the sorted tuple of `(bridge_id, is_open)` pairs.
It matters because switches can open, close, or toggle bridges and thereby
change which later moves are safe. Each successor uses a cloned board, so
search branches do not mutate one another or the source board.

The search key in `BFSSolver._state_key()` combines the block's
`canonical_key()` with the board's bridge-state key. The rest of the level
layout, switches, and teleporter definitions remain fixed during one search.

### Actions

The solver considers:

- `UP`, `RIGHT`, `DOWN`, and `LEFT` rolls.
- `_` to switch the active cube when the block is split.

Every action has unit cost. Switching is a distinct search step even though it
does not move either cube.

### Transition model

For a directional action, BFS clones the current board, assigns the current
block to a `Game` instance, and calls `Game.roll(direction)`. The game and board
apply the relevant rules, including:

- Whether all occupied cells are supported by walkable tiles.
- Fragile-tile behavior for a standing normal block.
- Soft-switch activation by contact and heavy-switch activation by a standing
  normal block.
- Teleport split destinations and the teleporter's selected active cube.
- Split-cube movement, cube switching, and re-merging when the cubes become
  adjacent.
- Victory when the normal block stands on the goal.

Only successors with outcomes `SAFE`, `MERGED`, `TELEPORT`, or `VICTORY` are
added to the search. Falling outcomes are rejected. For a split state, the
solver also generates the `_` successor using `Game.switch_block()`.

### Goal test

The goal test delegates to `BaseSolver.is_goal()`, which asks the board to
evaluate the block state. The block must be standing on the goal tile. A split
cube on a goal tile is not itself a victory; the split state must be brought
back to a normal block state that satisfies the goal rule.

### Cost function and heuristic

Each roll and each split-cube switch costs `1`. The path cost is therefore the
number of actions in the returned `moves` list. BFS uses no heuristic; it is an
uninformed search. Because all edges have equal cost, the first goal dequeued
has the fewest solver actions.

## Avoiding repeated states

BFS records a state's key in `visited` when it is enqueued. Any later path that
reaches the same canonical block state with the same bridge configuration is
skipped. Recording on discovery prevents duplicate queue entries. Including
bridge state prevents BFS from merging configurations that can have different
future legal moves.

`visited_count` counts dequeued states, including the goal state if one is
found. `expanded_nodes` counts dequeued non-goal states for which BFS attempts
to generate successors. `max_depth` is the greatest path length dequeued.

## Correctness properties

The guarantees below assume a finite board, a finite set of bridge
configurations, deterministic game rules, and a state key that includes every
piece of persistent state that can affect future transitions. They also assume
the successor generator represents every legal roll and split switch.

### Completeness

If a goal is reachable, BFS eventually finds it. Each discovered state is
enqueued at most once, and each state has finitely many actions. The reachable
state graph is finite: normal block positions have a finite number of
coordinates and orientations; split states have a finite number of cube
coordinate pairs and active-cube choices; bridge configurations are finite.
Consequently BFS either dequeues a reachable goal or exhausts the reachable
states.

### Shortest-path optimality

Let `d(s)` be the minimum number of actions from the start to state `s`.

1. BFS enqueues the start at depth zero.
2. When a state at depth `d` is expanded, each newly discovered successor is
   enqueued at depth `d + 1`.
3. FIFO order processes states in nondecreasing depth.

Thus, when BFS dequeues its first goal, no goal reachable in fewer actions can
remain undiscovered: the predecessor on any shorter path would have been
expanded first. The returned solution is shortest in rolls plus split-switch
actions. It is not necessarily shortest in elapsed time or any objective that
assigns different costs to actions.

## Performance metrics

`BFSSolver.search()` returns a `BFSSolverResult`, whose `summary()` reports:

| Metric | Meaning |
| --- | --- |
| Moves | Number of actions in the solution (`len(moves)`). |
| Visited States | Number of states dequeued and evaluated. |
| Depth | Maximum dequeued path length; on success, the solution depth. |
| Search Time | Elapsed search time in milliseconds, measured with `perf_counter()`. |
| Peak Memory | Peak traced Python allocation in KiB, measured with `tracemalloc`. |
| Expanded Nodes | Number of dequeued non-goal states whose successors are generated. |

Peak traced memory is not total process memory (RSS) and does not include all
native allocations. If `tracemalloc` was already active before a search, its
reported peak is the high-water mark of that existing tracing session and may
include earlier allocations. Otherwise, BFS starts tracing for the search and
stops it when the search returns.

## Benchmarking every stage

The benchmark utility solves each `stage_*.json` file in the levels directory
with BFS, writes a CSV report, and creates line plots for search time and peak
memory. Run it from the project root:

```powershell
.\.venv\Scripts\python.exe -m bloxorz.solvers.benchmark_bfs
```

Or, with the virtual environment activated:

```bash
python -m bloxorz.solvers.benchmark_bfs
```

The default output directory is `docs/algo/bfs/`:

- [`bfs_stage_statistics.csv`](bfs_stage_statistics.csv) contains one row per
  stage, including the exact `summary()` text and separate metric columns. A
  final `Average` row reports the arithmetic mean of move length, visited
  states, depth, search time, peak memory, and expanded nodes across the
  processed stages.
- [`bfs_search_time.png`](bfs_search_time.png) plots stage number on the x-axis
  and search time in milliseconds on the y-axis.
- [`bfs_peak_memory.png`](bfs_peak_memory.png) plots stage number on the x-axis
  and peak traced memory in KiB on the y-axis.

### Generated benchmark plots

![BFS search time by stage](bfs_search_time.png)

![BFS peak memory by stage](bfs_peak_memory.png)

The benchmark reads stage files in numeric stage order. It includes every
matching stage in the CSV and average, including a failed search if a stage has
no solution. Search time and memory can vary between runs and machines; these
single-run plots are useful for comparison, not as hardware-independent
performance guarantees.

## Strengths

- **Shortest solution by action count:** BFS is optimal for unit-cost rolls and
  cube switches, with no heuristic required.
- **Complete on the finite modeled state graph:** if a solution is reachable
  through legal transitions, BFS can find it.
- **Handles dynamic mechanics:** the search state includes bridge
  configuration, and transitions reuse the game's switch, teleport, split,
  merge, and goal rules.
- **Straightforward to reason about:** FIFO layers and a visited set make its
  completeness and shortest-path argument easy to verify.
- **Useful comparison baseline:** the benchmark metrics can be compared with
  informed search algorithms such as A*.

## Weaknesses and implementation caveats

- **Memory use grows with the explored graph.** Abstract BFS requires `O(V)`
  space for visited states and queue entries, where `V` is the number of
  reachable states. This implementation also stores a complete path in every
  queued entry, so path storage can approach `O(V D)` for maximum search depth
  `D`. Successor generation clones board data as well.
- **Split states expand the state space.** In addition to normal block
  positions and orientations, the solver must account for two cube positions
  and which cube is active.
- **Bridge combinations multiply states.** With `k` independent bridge groups,
  up to `2^k` bridge configurations may accompany a geometric block state.
- **No heuristic guidance.** BFS explores shallower states regardless of
  whether they seem closer to the goal; large or distant puzzles can take more
  time and memory than an informed search.
- **Uniform-cost limitation.** BFS minimizes the number of actions, not total
  weighted cost. Dijkstra's algorithm is appropriate for unequal
  nonnegative costs; A* may be used with a suitable admissible heuristic.
- **Correctness depends on model completeness.** If a new mechanic introduces
  persistent state, that state must be included in the canonical key and
  preserved by board cloning and successor generation.

In graph terms, BFS takes `O(V + E)` time and `O(V)` space when state-key
operations and successor generation are treated as constant time. In this
implementation, board cloning, bridge-state key construction, and path copying
add costs proportional to the relevant board and path sizes.
