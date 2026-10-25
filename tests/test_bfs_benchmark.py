import subprocess
import sys
from pathlib import Path


def test_benchmark_script_can_be_run_directly_outside_project_root(tmp_path):
    project_root = Path(__file__).parent.parent
    benchmark_script = project_root / "bloxorz" / "solvers" / "benchmark_bfs.py"
    output_dir = tmp_path / "report"

    result = subprocess.run(
        [
            sys.executable,
            str(benchmark_script),
            "--levels-dir",
            str(project_root / "bloxorz" / "levels"),
            "--output-dir",
            str(output_dir),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "bfs_stage_statistics.csv").is_file()
    assert (output_dir / "bfs_search_time.png").is_file()
    assert (output_dir / "bfs_peak_memory.png").is_file()
