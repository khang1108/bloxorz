"""Unit tests for BaseBlockState, NormalBlockState, SingleBlock, and SplitBlockState."""

from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block import (
    BaseBlockState,
    NormalBlockState,
    SplitBlockState,
    SingleBlock,
    BlockState,
)


class TestNormalBlockState:
    """Verifies NormalBlockState behavior and BaseBlockState compliance."""

    def test_polymorphism_and_properties(self):
        block = NormalBlockState(3, 4, BlockOrientation.STANDING)
        assert isinstance(block, BaseBlockState)
        assert block.is_split is False
        assert block.occupied_cells == {(3, 4)}

    def test_backward_compatibility_alias(self):
        assert BlockState is NormalBlockState
        block = BlockState(1, 2, BlockOrientation.LYING_X)
        assert block.is_split is False
        assert block.occupied_cells == {(1, 2), (2, 2)}

    def test_canonical_key(self):
        b1 = NormalBlockState(2, 3, BlockOrientation.STANDING)
        b2 = NormalBlockState(2, 3, BlockOrientation.STANDING)
        assert b1.canonical_key() == b2.canonical_key()
        assert b1.canonical_key() == (False, 2, 3, BlockOrientation.STANDING)


class TestSingleBlock:
    """Verifies SingleBlock 1x1x1 cube kinematics."""

    def test_single_block_movement(self):
        cube = SingleBlock(5, 5)
        assert cube.move(Direction.RIGHT) == SingleBlock(6, 5)
        assert cube.move(Direction.LEFT) == SingleBlock(4, 5)
        assert cube.move(Direction.UP) == SingleBlock(5, 4)
        assert cube.move(Direction.DOWN) == SingleBlock(5, 6)

    def test_single_block_geometry(self):
        cube = SingleBlock(2, 7)
        assert cube.get_center_3d() == (2.0, 7.0, 0.5)
        assert cube.get_dimensions_3d() == (1.0, 1.0, 1.0)


class TestSplitBlockState:
    """Verifies SplitBlockState behavior, switching, movement, and merging."""

    def test_split_block_properties(self):
        b1 = SingleBlock(2, 3)
        b2 = SingleBlock(8, 9)
        state = SplitBlockState(b1, b2, active_index=0)

        assert isinstance(state, BaseBlockState)
        assert state.is_split is True
        assert state.occupied_cells == {(2, 3), (8, 9)}
        assert state.active_block == b1
        assert state.passive_block == b2

    def test_switch_active_block(self):
        b1 = SingleBlock(2, 3)
        b2 = SingleBlock(8, 9)
        state0 = SplitBlockState(b1, b2, active_index=0)
        assert state0.active_block == b1

        # Switch to block 2
        state1 = state0.switch_active()
        assert state1.active_index == 1
        assert state1.active_block == b2
        assert state1.passive_block == b1

        # Switch back to block 1
        state2 = state1.switch_active()
        assert state2.active_index == 0
        assert state2.active_block == b1

    def test_move_active_block(self):
        b1 = SingleBlock(2, 3)
        b2 = SingleBlock(8, 9)
        state = SplitBlockState(b1, b2, active_index=0)

        # Move active block (b1) RIGHT: (2, 3) -> (3, 3), b2 stays at (8, 9)
        next_state = state.move_active(Direction.RIGHT)
        assert next_state.b1 == SingleBlock(3, 3)
        assert next_state.b2 == SingleBlock(8, 9)
        assert next_state.active_index == 0

        # Roll method delegates to move_active
        roll_state = state.roll(Direction.RIGHT)
        assert roll_state == next_state

        # Switch to b2 and move DOWN: (8, 9) -> (8, 10), b1 stays at (2, 3)
        state_b2 = state.switch_active().move_active(Direction.DOWN)
        assert state_b2.b1 == SingleBlock(2, 3)
        assert state_b2.b2 == SingleBlock(8, 10)
        assert state_b2.active_index == 1

    def test_check_merge_horizontal(self):
        # b1 at (4, 5) and b2 at (5, 5) -> Manhattan dist = 1 -> Merges into LYING_X
        state = SplitBlockState(SingleBlock(4, 5), SingleBlock(5, 5))
        merged = state.check_merge()
        assert merged is not None
        assert isinstance(merged, NormalBlockState)
        assert merged.x == 4
        assert merged.y == 5
        assert merged.orientation == BlockOrientation.LYING_X
        assert merged.occupied_cells == {(4, 5), (5, 5)}

    def test_check_merge_vertical(self):
        # b1 at (3, 7) and b2 at (3, 6) -> Manhattan dist = 1 -> Merges into LYING_Y
        state = SplitBlockState(SingleBlock(3, 7), SingleBlock(3, 6))
        merged = state.check_merge()
        assert merged is not None
        assert isinstance(merged, NormalBlockState)
        assert merged.x == 3
        assert merged.y == 6
        assert merged.orientation == BlockOrientation.LYING_Y
        assert merged.occupied_cells == {(3, 6), (3, 7)}

    def test_check_merge_not_adjacent(self):
        # Manhattan dist = 2 -> No merge
        state = SplitBlockState(SingleBlock(3, 3), SingleBlock(5, 3))
        assert state.check_merge() is None

        # Diagonal distance (dx=1, dy=1 -> Manhattan dist = 2) -> No merge
        state_diag = SplitBlockState(SingleBlock(3, 3), SingleBlock(4, 4))
        assert state_diag.check_merge() is None

    def test_canonical_key_symmetry(self):
        """(A, B, active=0) and (B, A, active=1) refer to the exact same game state."""
        b_a = SingleBlock(3, 4)
        b_b = SingleBlock(7, 8)

        state1 = SplitBlockState(b_a, b_b, active_index=0)
        state2 = SplitBlockState(b_b, b_a, active_index=1)

        assert state1.canonical_key() == state2.canonical_key()

    def test_from_targets_factory(self):
        state = SplitBlockState.from_targets(target_1=(10, 1), target_2=(10, 7), selected=1)
        assert state.b1 == SingleBlock(10, 1)
        assert state.b2 == SingleBlock(10, 7)
        assert state.active_index == 1
        assert state.active_block == SingleBlock(10, 7)
