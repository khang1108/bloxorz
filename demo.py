"""Demo script to run and visualize DFS and Split mechanics in terminal."""

import sys
from pathlib import Path

# Force UTF-8 stdout encoding on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from bloxorz.core.level_loader import load_level_from_file
from bloxorz.core.game import Game
from bloxorz.solvers.dfs import DFSSolver, IDSSolver


def print_stage_demo(stage_num: int, use_ids: bool = False):
    stage_file = root_dir / "bloxorz" / "levels" / f"stage_{stage_num:02d}.json"
    if not stage_file.exists():
        print(f"Error: Stage {stage_num:02d} not found at {stage_file}")
        return

    board = load_level_from_file(stage_file)
    algo_name = "IDS (Iterative Deepening)" if use_ids else "DFS (Depth-First Search)"
    solver = IDSSolver(max_depth=30) if use_ids else DFSSolver(max_depth=5000)

    print("=" * 70)
    print(f"  DEMO: {board.level_name.upper()} | THUẬT TOÁN: {algo_name}")
    print(f"  Số lượng ô: {len(board.base_tiles)} | Cầu: {len(board.bridges)} | Switch: {len(board.switches)} | Teleport: {len(board.teleports)}")
    print("=" * 70)

    print("\n[1] Đang chạy tìm kiếm lời giải...")
    result = solver.solve(board)

    print("\n[2] KẾT QUẢ THU ĐƯỢC:")
    print(f"  - Trạng thái: {'THÀNH CÔNG (SOLVED)' if result.is_solved else 'THẤT BẠI'}")
    print(f"  - Số bước đi: {len(result.moves)} bước")
    print(f"  - Số nút mở rộng (Expanded Nodes): {result.expanded_nodes}")
    print(f"  - Tổng số trạng thái đã duyệt (Visited States): {result.visited_count}")
    print(f"  - Thời gian tìm kiếm: {result.execution_time_ms:.2f} ms")
    print(f"  - Bộ nhớ RAM đỉnh (Peak Memory): {result.peak_memory_kb:.2f} KB")

    move_symbols = [m.name for m in result.moves]
    print(f"\n[3] Chuỗi các bước đi:")
    print("  -> " + " -> ".join(move_symbols))

    print("\n[4] Kiểm tra mô phỏng thực tế (Game Replay):")
    game = Game(board)
    step_num = 1
    for m in result.moves:
        outcome, block, _ = game.roll(m)
        split_info = " [Đang tách thành 2 khối]" if block.is_split else f" [{block.orientation.name}]"
        print(f"  Bước {step_num:02d}: Lệnh {m.name:<11} | Kết quả: {outcome:<7} | Khối:{split_info}")
        step_num += 1

    print(f"\n=> KẾT LUẬN: Đã đưa khối về đích an toàn ({game.status.name})!\n")


def main():
    print("\n" + "#" * 70)
    print("#  BLOXORZ SOLVER - DEMO CHẠY THỬ NHIỆM VỤ MEMBER 3 (DFS & SPLIT)")
    print("#" * 70 + "\n")

    # Demo 1: Màn cơ bản Stage 01 bằng IDS (tối ưu 7 bước)
    print_stage_demo(stage_num=1, use_ids=True)

    # Demo 2: Màn cầu & switch phức tạp Stage 05 bằng DFS (vừa sửa lỗi)
    print_stage_demo(stage_num=5, use_ids=False)

    # Demo 3: Màn phân tách khối Stage 08 bằng DFS
    print_stage_demo(stage_num=8, use_ids=False)


if __name__ == "__main__":
    main()
