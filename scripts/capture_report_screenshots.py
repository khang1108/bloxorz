#!/usr/bin/env python3
"""Automated high-resolution screenshot generator for Bloxorz report."""

import os
import sys
import time
from pathlib import Path

# Set project root
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ursina import Ursina, window, color, Vec3
from bloxorz.config import CONFIG

# Configure high-res 1920x1080 window
CONFIG.window.width = 1920
CONFIG.window.height = 1080
CONFIG.window.fullscreen = False

app = Ursina()
from direct.showbase.ShowBaseGlobal import base
from bloxorz.main import BloxorzApp
from bloxorz.core.block.split import SplitBlockState, SingleBlock
from bloxorz.core.constants import Direction

bloxorz = BloxorzApp()
images_dir = root_dir / "docs/report/images"
images_dir.mkdir(parents=True, exist_ok=True)

def step_frames(count: int = 15):
    for _ in range(count):
        app.step()

# --- 1. Stage Select Menu ---
print("[1/6] Capturing stage select menu...")
bloxorz.menu_mgr.show_stage_select_menu(current_stage=1, page=1)
step_frames(20)
base.screenshot(str(images_dir / "menu_stages.png"), defaultFilename=False)
bloxorz.menu_mgr.close_all()
step_frames(10)

# --- 2. 3D Gameplay & Tactical Minimap (Stage 01) ---
print("[2/6] Capturing 3D gameplay & minimap (Stage 01)...")
bloxorz.load_stage_by_index(1, animate_camera=False)
bloxorz.hud.update_moves(0)
bloxorz.solver_widget.current_algorithm = "BFS"
bloxorz.set_active_solver("BFS")
bloxorz._sync_minimap()
step_frames(25)
base.screenshot(str(images_dir / "game_gui_3d.png"), defaultFilename=False)

# --- 3. Fragile Orange Tiles (Stage 04) ---
print("[3/6] Capturing fragile tiles mechanic (Stage 04)...")
bloxorz.load_stage_by_index(4, animate_camera=False)
bloxorz.hud.update_moves(2)
bloxorz.solver_widget.current_algorithm = "A*"
bloxorz.set_active_solver("A*")
bloxorz._sync_minimap()
step_frames(25)
base.screenshot(str(images_dir / "gameplay_fragile.png"), defaultFilename=False)

# --- 4. Bridge & Switch Mechanic (Stage 02) ---
print("[4/6] Capturing bridge & switches mechanic (Stage 02)...")
bloxorz.load_stage_by_index(2, animate_camera=False)
bloxorz.hud.update_moves(4)
bloxorz.solver_widget.current_algorithm = "UCS"
bloxorz.set_active_solver("UCS")
bloxorz._sync_minimap()
step_frames(25)
base.screenshot(str(images_dir / "gameplay_bridge.png"), defaultFilename=False)

# --- 5. Split / Teleport Bifurcation Mechanic (Stage 08) ---
print("[5/6] Capturing split / teleport mechanic (Stage 08)...")
bloxorz.load_stage_by_index(8, animate_camera=False)
# Set split state on Stage 08: b1 at (10, 1), b2 at (10, 7)
split_st = SplitBlockState(
    b1=SingleBlock(10, 1),
    b2=SingleBlock(10, 7),
    active_index=0
)
bloxorz.game.block = split_st
bloxorz.block_view.sync_to_state(split_st)
bloxorz.hud.set_split_mode(True)
bloxorz.hud.update_moves(7)
bloxorz.solver_widget.current_algorithm = "DFS"
bloxorz.set_active_solver("DFS")
bloxorz._sync_minimap()
step_frames(25)
base.screenshot(str(images_dir / "gameplay_split.png"), defaultFilename=False)

# --- 6. AI Solver Execution & Automation ---
print("[6/6] Capturing AI Solver execution...")
bloxorz.load_stage_by_index(1, animate_camera=False)
bloxorz.solver_widget.set_running_state(True)
bloxorz.solver_widget.status_text.text = "A* SOLVING · OPTIMAL SEARCH"
bloxorz.hud.update_moves(6)
bloxorz._sync_minimap()
step_frames(25)
base.screenshot(str(images_dir / "gameplay_solver.png"), defaultFilename=False)

print("All screenshots successfully captured!")
