# Bloxorz Data & Stage Archive

This directory catalogs the datasets, maps, and optimal solution benchmarks harvested and normalized from open-source GitHub repositories for the classic 33-stage puzzle game **Bloxorz**.

---

## 1. Upstream GitHub Repositories

| Repository | Author | Key Contributions & Artifacts |
|---|---|---|
| [**`tkoz0/bloxorz-solver`**](https://github.com/tkoz0/bloxorz-solver) | `@tkoz0` | Canonical 33-stage CoolMath Bloxorz data (`coolmath.json`), bridge & switch mechanics, and verified minimal move counts totaling **1,999 moves** (`solution.txt`). |
| [**`phamquiluan/BloxorzSolver`**](https://github.com/phamquiluan/BloxorzSolver) | `@phamquiluan` | 33 ASCII text level maps (`map01.txt` .. `map33.txt`), BFS / DFS / Best-First Search pathfinders. |
| [**`sethbfey/Bloxorz-DDQN`**](https://github.com/sethbfey/Bloxorz-DDQN) | `@sethbfey` | Reinforcement Learning gymnasium environment with level layouts and bridge metadata. |
| [**`Erroler/Bloxorz`**](https://github.com/Erroler/Bloxorz) | `@Erroler` | Python graphical recreation and state transition algorithms. |

---

## 2. Data Structure in this Repository

- **[`bloxorz/levels/`](file:///home/phuckhang/MyWorkspace/boxorz_solvers/bloxorz/levels):** Production stage definitions (`stage_01.json` through `stage_33.json`) parsed and loaded directly by the game engine and external solvers.
- **[`data/coolmath.json`](file:///home/phuckhang/MyWorkspace/boxorz_solvers/data/coolmath.json):** Full upstream dataset of all 33 original stages with CoolMath passcodes, grid representations, bridge groupings, and multi-action switches.
- **[`data/solutions.json`](file:///home/phuckhang/MyWorkspace/boxorz_solvers/data/solutions.json):** Ground-truth optimal solution move sequences (`U`, `D`, `L`, `R`) and minimal step counts for every stage.
- **[`data/external_maps/`](file:///home/phuckhang/MyWorkspace/boxorz_solvers/data/external_maps):** Raw text map benchmarks (`map01.txt` .. `map33.txt`) from `phamquiluan/BloxorzSolver`.

---

## 3. Official 33 Stages Master Catalog

| Stage | Passcode | Grid Size | Bridges | Switches | Teleports | Optimal Moves |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **01** | `780464` | 6 × 10 | 0 | 0 | 0 | **7** |
| **02** | `290299` | 6 × 15 | 2 | 2 | 0 | **17** |
| **03** | `918660` | 6 × 15 | 0 | 0 | 0 | **19** |
| **04** | `520967` | 9 × 14 | 0 | 0 | 0 | **28** |
| **05** | `028431` | 10 × 15 | 3 | 4 | 0 | **33** |
| **06** | `524383` | 10 × 15 | 0 | 0 | 0 | **35** |
| **07** | `189493` | 8 × 15 | 1 | 1 | 0 | **44** |
| **08** | `499707` | 9 × 15 | 0 | 0 | 1 | **10** |
| **09** | `074355` | 5 × 15 | 0 | 0 | 1 | **24** |
| **10** | `300590` | 10 × 14 | 3 | 2 | 1 | **57** |
| **11** | `291709` | 10 × 12 | 1 | 1 | 0 | **47** |
| **12** | `958640` | 10 × 13 | 2 | 2 | 0 | **65** |
| **13** | `448106` | 10 × 14 | 0 | 0 | 0 | **46** |
| **14** | `210362` | 10 × 14 | 2 | 2 | 0 | **67** |
| **15** | `098598` | 10 × 15 | 4 | 4 | 1 | **57** |
| **16** | `000241` | 8 × 13 | 2 | 2 | 5 | **28** |
| **17** | `683596` | 10 × 15 | 4 | 5 | 0 | **106** |
| **18** | `284933` | 9 × 15 | 4 | 6 | 0 | **85** |
| **19** | `119785` | 10 × 15 | 2 | 3 | 0 | **67** |
| **20** | `543019` | 10 × 15 | 3 | 5 | 1 | **56** |
| **21** | `728724` | 10 × 15 | 2 | 2 | 0 | **71** |
| **22** | `987319` | 10 × 14 | 3 | 4 | 0 | **65** |
| **23** | `293486` | 10 × 15 | 6 | 4 | 1 | **75** |
| **24** | `088198` | 8 × 14 | 4 | 4 | 1 | **57** |
| **25** | `250453` | 10 × 14 | 5 | 3 | 0 | **55** |
| **26** | `426329` | 9 × 14 | 3 | 2 | 1 | **104** |
| **27** | `660141` | 10 × 15 | 2 | 3 | 0 | **71** |
| **28** | `769721` | 10 × 15 | 2 | 1 | 1 | **100** |
| **29** | `691859` | 10 × 15 | 9 | 6 | 0 | **104** |
| **30** | `280351` | 10 × 15 | 4 | 3 | 0 | **114** |
| **31** | `138620` | 10 × 15 | 6 | 5 | 0 | **91** |
| **32** | `879021` | 9 × 14 | 4 | 3 | 0 | **129** |
| **33** | `614955` | 10 × 15 | 3 | 13 | 0 | **65** |
| **TOTAL** | — | — | **84** | **83** | **17** | **1,999** |

---

## 4. Native Stage JSON Specification

All stage files in `bloxorz/levels/` adhere to the following schema:

```json
{
  "name": "Stage 02",
  "passcode": "290299",
  "spawn": {
    "x": 1,
    "y": 4,
    "orientation": "STANDING"
  },
  "layout": [
    "......1111..111",
    "1111..11H1..121",
    "11S1..1111..111",
    "1111..1111..111",
    "1111BB1111BB111",
    "1111..1111....."
  ],
  "bridges": [
    {
      "id": "b1",
      "tiles": [[4, 4], [5, 4]],
      "initially_open": false
    }
  ],
  "switches": [
    {
      "x": 2,
      "y": 2,
      "type": "SOFT",
      "targets": ["b1"],
      "actions": {
        "b1": "TOGGLE"
      },
      "action": "TOGGLE"
    }
  ],
  "teleports": []
}
```

### Tile Legend in `layout` Strings:
- `.` / `' '` : VOID (chasm / fall off)
- `1` : NORMAL durable stone tile
- `2` / `G` : GOAL hole
- `3` / `-` : FRAGILE orange tile (collapses if standing upright)
- `S` : SOFT switch (circular plate, triggers on any contact)
- `H` / `X` : HEAVY switch (cross plate, triggers only when standing upright)
- `B` : BRIDGE tile (initially closed)
- `8` / `T` : TELEPORT / Splitter tile
