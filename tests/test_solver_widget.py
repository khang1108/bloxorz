"""Unit tests for SolverWidget and multi-algorithm solver selection."""

from unittest.mock import MagicMock
from bloxorz.ui.solver_widget import SolverWidget
from bloxorz.ui.constants import SolverWidgetConstants
from bloxorz.solvers import (
    SOLVER_REGISTRY,
    get_solver,
    BFSSolver,
)
from bloxorz.main import BloxorzApp


def test_solver_registry_completeness():
    """Verifies that BFS is implemented and DFS/UCS are marked as coming soon."""
    assert "BFS" in SOLVER_REGISTRY
    assert "DFS" in SOLVER_REGISTRY
    assert "UCS" in SOLVER_REGISTRY
    assert "A*" in SOLVER_REGISTRY

    from bloxorz.solvers.ucs import UCSSolver

    assert isinstance(get_solver("BFS"), BFSSolver)
    assert get_solver("DFS") is None
    assert isinstance(get_solver("UCS"), UCSSolver)


def test_solver_widget_initial_state():
    """Widget starts collapsed with BFS selected and text sizes stable."""
    mock_select = MagicMock()
    mock_run = MagicMock()

    widget = SolverWidget(
        parent=None,
        on_select_algorithm=mock_select,
        on_run_solver=mock_run,
        initial_algorithm="BFS",
    )

    assert widget.is_expanded is False
    assert widget.current_algorithm == "BFS"
    assert widget.collapsed_btn.visible is True
    assert widget.expanded_root.visible is False
    assert "BFS" in widget.collapsed_btn.text

    # Verify stable text scale on buttons to prevent hover shrinking bug
    assert widget.collapsed_btn.text_size == widget.collapsed_btn.highlight_text_size
    assert widget.action_btn.text_size == widget.action_btn.highlight_text_size
    for btn in widget.option_buttons.values():
        assert btn.text_size == btn.highlight_text_size


def test_solver_widget_collapse_expand_toggle():
    """Test switching between collapsed and expanded states."""
    widget = SolverWidget(parent=None, initial_algorithm="BFS")

    assert widget.is_expanded is False
    assert widget.collapsed_btn.visible is True
    assert widget.expanded_root.visible is False

    widget.expand()
    assert widget.is_expanded is True
    assert widget.collapsed_btn.visible is False
    assert widget.expanded_root.visible is True

    widget.collapse()
    assert widget.is_expanded is False
    assert widget.collapsed_btn.visible is True
    assert widget.expanded_root.visible is False

    widget.toggle_collapse()
    assert widget.is_expanded is True
    widget.toggle_collapse()
    assert widget.is_expanded is False


def test_solver_widget_select_algorithms():
    """Selecting an algorithm updates current_algorithm, radio labels, and fires callback."""
    mock_select = MagicMock()
    widget = SolverWidget(
        parent=None,
        on_select_algorithm=mock_select,
        initial_algorithm="BFS",
    )

    for algo in ("DFS", "UCS", "A*", "BFS"):
        widget.select_algorithm(algo)
        assert widget.current_algorithm == algo
        assert algo in widget.collapsed_btn.text
        assert "(*)" in widget.option_buttons[algo].text

        # Verify coming soon indicator on unready algorithms
        if algo in widget.COMING_SOON:
            assert "[SOON]" in widget.option_buttons[algo].text
            assert "[SOON]" in widget.collapsed_btn.text

        # Other options should not be marked selected
        for other_algo, btn in widget.option_buttons.items():
            if other_algo != algo:
                assert "( )" in btn.text

        mock_select.assert_called_with(algo)


def test_solver_widget_action_button_and_running_state():
    """Action button triggers run callback and changes label on running state."""
    mock_run = MagicMock()
    widget = SolverWidget(parent=None, on_run_solver=mock_run)

    widget.action_btn.on_click()
    mock_run.assert_called_once()

    widget.set_running_state(True)
    assert widget.is_running is True
    assert "STOP" in widget.action_btn.text

    widget.set_running_state(False)
    assert widget.is_running is False
    assert "RUN" in widget.action_btn.text


def test_solver_widget_set_visible():
    """Visibility toggle controls the root entity."""
    widget = SolverWidget(parent=None)
    widget.set_visible(False)
    assert widget.root.visible is False
    widget.set_visible(True)
    assert widget.root.visible is True


def test_app_set_active_solver_integration():
    """Test BloxorzApp switching active solver and handling coming soon."""
    app = BloxorzApp.__new__(BloxorzApp)
    app.registered_solver = None
    app.active_solver_name = "BFS"
    app.solver_widget = MagicMock()
    app.solver_widget.current_algorithm = "BFS"
    app.game = MagicMock()
    app.block_view = MagicMock()
    app.block_view.is_animating = False
    app._is_playing_solution = False
    app.hud = MagicMock()

    # Selecting DFS (coming soon)
    app.set_active_solver("DFS")
    assert app.active_solver_name == "DFS"
    assert app.registered_solver is None
    app.solver_widget.select_algorithm.assert_called_with("DFS")

    # Triggering solver on coming soon algorithm displays coming soon banner
    app.trigger_solver()
    app.hud.show_banner.assert_called_with("DFS: COMING SOON", duration=1.5)

    # Selecting BFS
    app.set_active_solver("BFS")
    assert app.active_solver_name == "BFS"
    assert isinstance(app.registered_solver, BFSSolver)


def test_solver_widget_constants():
    """Verify SolverWidgetConstants values."""
    assert SolverWidgetConstants.COLLAPSED_POS == (0.70, 0.36)
    assert SolverWidgetConstants.EXPANDED_POS == (0.70, 0.22)
    assert SolverWidgetConstants.EXPANDED_CONTAINER_SCALE == (0.24, 0.26)
    assert len(SolverWidgetConstants.OPTION_BTN_SCALE) == 2
