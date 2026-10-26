# Uniform-Cost Search (UCS) for Bloxorz

UCS finds a sequence of actions from the stage's spawn state to victory with
the lowest total route cost. The default cost balances physical movement
against contact with fragile tiles, so a minimum-cost solution may require
more rolls than another valid route.

The implementation is in [ucs.py](../../../bloxorz/solvers/ucs.py), with
[shared transition rules](../../../bloxorz/solvers/base.py) and a
[shared cost function](../../../bloxorz/solvers/costs.py). See the
[UCS usage guide](../../ucs.md) for API and playback details.

## Search problem formulation

### State representation

A search state consists of the block configuration and bridge configuration:

```text
state = (block_state, bridge_configuration)
```

The immutable block state has one of two forms:

- **Normal block:** anchor coordinates `(x, y)` and an orientation:
  - `STANDING` occupies `(x, y)`.
  - `LYING_X` occupies `(x, y)` and `(x + 1, y)`.
  - `LYING_Y` occupies `(x, y)` and `(x, y + 1)`.
- **Split block:** both cube positions and the currently active cube.
  Selecting a different cube changes the result of a directional action.

The bridge configuration is a sorted tuple of `(bridge_id, is_open)` pairs.
It must be part of the state key because bridge changes affect future legal
moves. The layout, switches, and teleport definitions remain fixed during
a search.

With the default cost, `block.canonical_key()` removes equivalent cube labels
while preserving the active cube's coordinate. For custom costs,
`_search_state_key()` preserves `b1`, `b2`, and `active_index` because the cost
function may distinguish cube labels. States may only be merged when their
future transitions and costs are equivalent.

### Start state and actions

Search starts at `board.spawn_state` on a freshly loaded board. The current
API does not accept a live block position; the GUI restarts the stage before
invoking UCS.

The actions are `UP`, `RIGHT`, `DOWN`, and `LEFT`. Split states also allow
`SWITCH`, which selects the other cube without moving either cube or
incrementing `Game.move_count`.

### Transition model

The graph is generated during search. Each edge represents a legal action
together with its effects, including switches, teleportation, splitting,
and merging.

`BaseSolver.get_successors()` tries each action on an independent
`Board.clone()` through `Game.roll()` or `Game.switch_block()`. The solver
therefore reuses the same core transitions as manual play without mutating
the input board.

After switch or teleport effects, the solver checks that all occupied cells
still support the block. Unsupported successors are rejected, including
those caused by a bridge closing beneath the passive cube or invalid
teleport destinations. Teleportation and merging are effects of movement,
not additional actions in the returned solution.

### Goal test

`BaseSolver.is_goal()` delegates to board evaluation. Victory requires the
normal block to stand upright on the goal tile. A split cube on the goal
does not complete the stage.

## Cost function

`fragile_cost(source_block, source_board, successor)` is evaluated only for
legal transitions:

| Action | Cost |
| --- | --- |
| Switch the active cube | 0 |
| Roll or move without a fragile surcharge | 1 |
| Roll or move with a fragile surcharge | 3 |

The surcharge depends on the source block state:

- **Normal block:** inspect occupied destination cells after all effects,
  including teleportation. Contact with at least one fragile tile adds 2.
  Contact with two fragile tiles still adds only 2.
- **Split block:** inspect only the moving cube's destination, including a
  movement that causes merging. A passive cube resting on fragile does not
  increase the cost of moving the other cube.
- Consecutive qualifying movements are charged separately. The surcharge
  does not count distinct fragile tiles visited.

Let `N` be the number of physical rolls or cube movements and `F` the number
of movements receiving the surcharge:

```text
solution_cost = N + 2 * F
```

The coefficient 2 expresses a route preference chosen by the team. It balances
fragile contact against route length and is not a measured probability of
falling. Changing it changes the optimization objective. Fragile contact can
still be preferred when avoiding it would require a sufficiently long detour.

Legality is separate from cost. A normal block standing on fragile is rejected
as a losing move. A normal block lying on fragile and a single cube resting
on fragile remain legal but may incur the surcharge.

`UCSSolver(cost_fn=...)` accepts an alternative cost function. It must be
deterministic, must not mutate its inputs, must depend only on information
represented by the state and transition, and must return a finite nonnegative
number. Invalid costs and accumulated-cost overflow raise `ValueError`.

## Search procedure

UCS uses a min-heap ordered by accumulated path cost `g(n)`:

```text
frontier = [(0, next_counter(), node(spawn))]
best_cost[key(spawn)] = 0

while frontier is not empty:
    node = pop the entry with the smallest cost
    if node.cost != best_cost[key(node.state)]:
        continue                         # stale entry

    if node.state satisfies the goal test:
        return reconstruct_path(node)

    increment expanded_nodes
    for successor in legal_successors(node.state):
        step_cost = cost_fn(node.state, successor)
        validate that step_cost is finite and nonnegative
        new_cost = node.cost + step_cost
        validate that new_cost is finite
        if new_cost < best_cost.get(key(successor), infinity):
            best_cost[key(successor)] = new_cost
            child = node(successor, new_cost, parent=node, action=successor.action)
            push (new_cost, next_counter(), child) into frontier

return failure
```

Heap entries have the form `(cost, counter, node)`. The increasing counter
breaks equal-cost ties in insertion order and avoids comparing node objects.
Successors are generated in the order `UP`, `RIGHT`, `DOWN`, `LEFT`, followed
by `SWITCH` for split states. Equal-cost solutions have no secondary ranking
by movement count or control-switch count.

Each immutable `SearchNode` (aliased as `_SearchNode`) stores its parent and incoming action. On
success, the solver follows the parent chain and reverses its actions to
reconstruct the playback sequence. Improved routes do not overwrite parent
records belonging to previously created nodes.

## Avoiding repeated states

`best_cost` records the lowest discovered cost for each state key. A later
route is accepted only when its cost is strictly lower. Permanently rejecting
a state after its first discovery could discard a cheaper route.

An improvement adds a new heap entry instead of removing the older entry
from the middle of the heap. The older entry is skipped when popped if its
cost no longer matches `best_cost`. Equal-cost cycles, including repeated
free control switches, do not produce further accepted entries.

## Correctness properties

These guarantees apply to the transition graph represented by the current
core and successor generator. They assume a finite board, deterministic
rules, a state key containing all information affecting future transitions
and costs, and nonnegative costs.

### Termination and completeness

Block positions, orientations, split-cube position pairs, active-cube choices,
and bridge configurations all have finitely many possibilities. Once a state
is popped with its best cost, a route through a more expensive state cannot
improve it because every edge cost is nonnegative. Each state is therefore
expanded at most once; stale entries are finite and eventually discarded.

Strict improvement rejects equal-cost cycles even when edges cost zero.
If a goal is reachable in the modeled graph, UCS eventually finds it.
Otherwise, the frontier is exhausted and `is_solved=False` is returned.

### Minimum-cost optimality

Suppose UCS pops a goal with cost `C` while a cheaper solution exists.
That route must contain a state still awaiting processing whose accumulated
cost is no greater than the route's total cost, since all edges are
nonnegative. Such a state would be selected before the goal of cost `C`,
contradicting the heap ordering. The returned solution therefore has
minimum total cost.

The goal test occurs after popping a non-stale entry. Merely generating a
goal is not a valid general stopping rule for arbitrary nonnegative costs.

Minimum cost does not imply the fewest physical movements, the fewest input
actions, or the shortest computation time.

## Relationship to BFS and A*

| Quantity | Meaning |
| --- | --- |
| `c(s, a, s')` | Cost of one legal transition |
| `g(n)` | Accumulated cost from spawn along the node's parent chain |
| `h(n)` | Estimated remaining cost from the current state to victory |

UCS orders the frontier by `g(n)` and uses no heuristic. A* orders it by
`g(n) + h(n)`; setting `h(n) = 0` gives UCS's priority rule.
`fragile_cost` is a step-cost function, not a heuristic.

An A* heuristic must be checked against orientation, splitting,
teleportation, fragile costs, and zero-cost control switches. Geometric
distance alone is not automatically a lower bound on remaining route cost.

The repository's BFS minimizes action count, including control switches.
Default UCS charges switches 0 and movements 1 or 3, so these solvers
optimize different objectives. Only when all edges share the same positive
cost does cost ordering correspond to BFS depth layers. Experiments should
distinguish action count, physical movement count, and route cost under a
shared evaluation function.

## Performance metrics

`UCSSolver.search()` returns `SolverResult`; `BaseSolver.solve()` adds timing:

| Field | Meaning |
| --- | --- |
| `is_solved` | Whether a solution was found |
| `moves` | Playback actions: `Direction` values and `"SWITCH"` |
| `solution_length` | Number of `Direction` actions, excluding control switches |
| `solution_cost` | Total route cost; `None` when unsolved |
| `visited_count` | Number of discovered keys, including keys still in the frontier |
| `expanded_nodes` | Successor-generation calls, excluding goals and stale entries |
| `max_depth` | Greatest physical movement count among expanded paths |
| `execution_time_ms` | Time spent in `search()`, measured by `solve()` |

`max_depth` is not necessarily the solution length. An initial goal produces
`is_solved=True`, `moves=[]`, and `solution_cost=0`; an empty action list alone
does not establish failure.

UCS does not currently measure peak memory itself. Memory measurement, CSV
export, plots, and comparative experiments belong to the benchmark task.

## Complexity

Let `V` be the number of reachable states and `E` their transitions.
Treating state-key operations, cost evaluation, and transition simulation as
constant time, the heap implementation with stale entries has an upper time
bound of `O((V + E) log(V + E))` and uses `O(V + E)` space.
Each state has at most five actions, so `E <= 5V`, giving `O(V log V)` time
and `O(V)` space under those assumptions.

Actual costs also include board cloning, stored board snapshots, and
bridge-state key construction. Parent pointers avoid copying the full action
sequence into each node, but older records can remain referenced by the
heap or child nodes.

## Strengths

- Finds minimum-cost solutions for unequal nonnegative action costs.
- Supports zero-cost control switches without accepting equal-cost cycles.
- Requires no heuristic to establish optimality.
- Reuses the core for bridges, switches, teleportation, split control,
  and merging.

## Weaknesses and implementation caveats

- Without a goal-directed estimate, many inexpensive states may be expanded
  before reaching a solution.
- The frontier, cost table, path records, and board snapshots can use
  substantial memory.
- With `N` floor positions, split-cube position pairs have `O(N^2)` possible
  combinations before legality filtering.
- With `k` independent bridge groups, up to `2^k` bridge configurations may
  accompany each geometric block state.
- Correctness under the intended game rules also depends on the core.
  Known issues are recorded in the [usage guide](../../ucs.md#tests-and-limitations).

## Verification and references

- [UCS tests](../../../tests/test_ucs.py): cheaper-route updates, stale entries,
  goal tests on pop, ties, zero-cost cycles, and invalid costs.
- [Split tests](../../../tests/test_split_solver.py): state keys,
  teleportation, control selection, merging, fragile surcharges, label-sensitive
  custom costs, and safe solution replay through `Game`.
- [Cost tests](../../../tests/test_costs.py): fragile surcharge conventions.
- [CMU 15-281: Search](https://www.cs.cmu.edu/~15281/coursenotes/search/):
  UCS, state-space graphs, completeness, and optimality.
- [Berkeley CS 188: Informed Search](https://inst.eecs.berkeley.edu/~cs188/textbook/search/informed.html):
  path costs, heuristics, A*, and heuristic requirements.
