"""Exercise one-click solver controls using real Ursina buttons without a display."""

import pytest
from ursina import camera, destroy
from bloxorz.ui.solver_widget import SolverWidget


@pytest.fixture
def controls(engine):
    selected = []
    executions = []
    widget = SolverWidget(
        parent=camera.ui,
        on_select_algorithm=selected.append,
        on_run_solver=lambda: executions.append(widget.current_algorithm),
    )
    yield widget, selected, executions
    destroy(widget.root)


@pytest.mark.parametrize('algorithm', ['BFS', 'DFS', 'UCS', 'A*'])
def test_one_click_selects_and_runs_the_labeled_solver(controls, algorithm):
    widget, selected, executions = controls
    widget.option_buttons[algorithm].on_click()
    assert selected == [algorithm]
    assert executions == [algorithm]


def test_busy_controls_cannot_switch_the_running_algorithm(controls):
    widget, selected, executions = controls
    widget.select_algorithm('UCS')
    selected.clear()
    widget.set_running_state(True)
    widget.option_buttons['DFS'].on_click()
    assert widget.current_algorithm == 'UCS'
    assert selected == []
    assert executions == []


def test_active_button_stops_instead_of_launching_another_solver(controls):
    widget, selected, executions = controls
    widget.select_algorithm('UCS')
    selected.clear()
    widget.set_running_state(True)
    widget.option_buttons['UCS'].on_click()
    assert selected == []
    assert executions == ['UCS']


def test_programmatic_selection_does_not_start_or_replace_a_solver(controls):
    widget, selected, executions = controls
    widget.select_algorithm('A*')
    assert widget.current_algorithm == 'A*'
    assert selected == []
    assert executions == []
