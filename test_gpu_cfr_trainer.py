import unittest
import numpy as np
import logging
from unittest.mock import MagicMock, patch
from gpu_cfr_trainer import GPUCFRTrainer

# Prevent the logger from writing to files during tests
logging.basicConfig(level=logging.CRITICAL)

class TestGpuCfrTrainer(unittest.TestCase):
    """Unit tests for the GPUCFRTrainer to diagnose infinite recursion issues."""

    def setUp(self):
        """Set up a trainer instance before each test."""
        # Mock the GPU-specific components to run tests on a CPU-only environment
        with patch('gpu_cfr_trainer.GPU_AVAILABLE', False):
            self.trainer = GPUCFRTrainer(use_gpu=False, num_players=2, small_blind=1, big_blind=2, initial_stack=200)
            # Mock external dependencies to isolate the logic
            self.trainer.equity_calculator = MagicMock()
            self.trainer.strategy_lookup = MagicMock()
            self.trainer.hand_evaluator = MagicMock()

    def test_recursion_limit_safeguard(self):
        """
        Verify that the recursion depth safeguard prevents infinite loops.
        This test uses a high starting recursion depth to trigger the safeguard.
        """
        player_hands = [['Ah', 'Ad'], ['Ks', 'Kd']]
        board = []
        pot = 3.0
        bets = np.array([1.0, 2.0])
        reach_probs = np.ones(2)
        active_players = np.array([True, True])
        player_stacks = np.array([199.0, 198.0])
        street = 0
        num_actions_this_street = 0

        # Start with a recursion depth close to the limit to trigger the safeguard
        result = self.trainer._cfr_recursive(
            player_hands, "", board, pot, bets, reach_probs, 
            active_players, player_stacks, street, num_actions_this_street, 
            recursion_depth=195  # Close to the 200 limit
        )
        
        # The function should return a terminal utility without crashing
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), self.trainer.num_players)

    def test_betting_round_termination_postflop(self):
        """
        Tests if a standard post-flop betting round (check, check) terminates correctly.
        An error here could lead to an infinite loop on a street.
        """
        # STATE: Post-flop (street 1), 2 players, both active.
        # Player 0 (SB) acts first.
        street = 1
        active_players = np.array([True, True])
        player_stacks = np.array([198.0, 198.0])
        num_can_act = np.sum(active_players & (player_stacks > 0))

        # SCENARIO: Player 0 checks, Player 1 checks.
        history = "kk"
        bets = np.array([0.0, 0.0])
        num_actions_this_street = 2

        # The round should be over.
        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        
        self.assertTrue(is_over, "A 'check-check' round post-flop should terminate the betting round.")

    def test_preflop_betting_round_termination_bb_option(self):
        """
        Tests if a pre-flop round terminates when action folds to the Small Blind,
        who calls, and the Big Blind checks. This is a common scenario that needs
        to be handled correctly to prevent loops.
        """
        # STATE: Pre-flop (street 0), 3 players. SB, BB, BTN.
        self.trainer.num_players = 3
        active_players = np.array([True, True, True])
        player_stacks = np.array([199.0, 198.0, 200.0])
        
        # SCENARIO: BTN folds, SB calls, BB checks.
        history = "fck" # Fold from BTN, Call from SB, Check from BB
        bets = np.array([2.0, 4.0, 0.0]) # SB calls to match BB (2.0), BB has big blind (4.0)
        active_players[2] = False # BTN folded
        num_actions_this_street = 3
        num_active = np.sum(active_players)

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, 0, num_actions_this_street, player_stacks)

        self.assertTrue(is_over, "Pre-flop round should end after the BB checks on their option.")

    def test_all_in_and_call_scenario(self):
        """
        Tests if the betting round correctly terminates when one player goes all-in
        and is called by another, leaving no further possible actions.
        """
        # STATE: Post-flop (street 1), 2 players.
        street = 1
        active_players = np.array([True, True])
        
        # SCENARIO: Player 0 bets, Player 1 raises all-in, Player 0 calls.
        history = "brc" # Bet, Raise, Call
        player_stacks = np.array([0.0, 150.0]) # Player 0 is now all-in.
        bets = np.array([50.0, 50.0])
        num_actions_this_street = 3

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)

        self.assertTrue(is_over, "Round should be over when an all-in is called.")

    def test_player_and_action_selection_in_recursion(self):
        """
        Verifies that the CFR recursive function terminates naturally without infinite loops
        and that player action selection works correctly in a realistic scenario.
        """
        # Set up a simple 2-player scenario that should terminate naturally
        self.trainer.num_players = 2
        player_hands = [['Ah', 'Ad'], ['Ks', 'Kd']]
        board = []
        pot = 3.0
        bets = np.array([1.0, 2.0])  # SB and BB
        reach_probs = np.ones(2)
        active_players = np.array([True, True])
        player_stacks = np.array([199.0, 198.0])
        street = 0
        num_actions_this_street = 0

        # Run the recursive function without mocking - it should terminate naturally
        try:
            result = self.trainer._cfr_recursive(
                player_hands, "", board, pot, bets, reach_probs, 
                active_players, player_stacks, street, num_actions_this_street, 
                recursion_depth=0
            )
            
            # Check that the recursion completed successfully
            self.assertIsNotNone(result, "CFR recursion should return a result")
            self.assertEqual(len(result), 2, "Result should have utilities for both players")
            self.assertLess(self.trainer.recursion_depth, 100, "Recursion depth should be reasonable")
            
        except Exception as e:
            self.fail(f"CFR recursion failed with exception: {e}")

    def test_all_in_player_cannot_act_again(self):
        """
        Tests that a player who is all-in is not asked to act again in the same betting round.
        """
        self.trainer.num_players = 3
        # Player 1 is all-in, Player 2 has a large stack, Player 0 has a medium stack.
        player_stacks = np.array([100.0, 50.0, 200.0])
        active_players = np.array([True, True, True])
        bets = np.array([20.0, 50.0, 20.0]) # P0 calls 20, P1 goes all-in for 50, P2 calls 20
        
        # It's Player 2's turn to act after Player 1's all-in.
        # We want to ensure the next player is Player 0, and not Player 1 (who is all-in).
        
        # Let's say Player 2 calls the all-in.
        player_stacks[2] -= 30 # P2 calls the extra 30
        bets[2] += 30

        # Now it should be Player 0's turn.
        next_player = self.trainer._get_current_player("rc", active_players, 1, 90, 3, player_stacks)
        self.assertEqual(next_player, 0, "The next player should be Player 0, not the all-in Player 1.")

    def test_complex_preflop_all_in_scenario(self):
        """
        Tests a multi-way, unequal all-in scenario pre-flop to ensure the round terminates.
        """
        self.trainer.num_players = 4
        # P0 (SB), P1 (BB), P2 (UTG), P3 (BTN)
        # P2 raises, P3 re-raises all-in (short stack), P0 folds, P1 calls all-in (medium stack), P2 calls.
        active_players = np.array([False, True, True, True]) # P0 folded
        player_stacks = np.array([199.0, 0.0, 80.0, 0.0]) # P1 and P3 are all-in
        bets = np.array([1.0, 120.0, 120.0, 50.0]) # P0 folded, P1 all-in for 120, P2 calls, P3 all-in for 50
        history = "rfaac" # UTG raises, BTN re-raises all-in, SB folds, BB calls all-in, UTG calls
        num_actions_this_street = 5

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, 0, num_actions_this_street, player_stacks)
        self.assertTrue(is_over, "The betting round should be over after all players are all-in or have folded.")

    def test_no_infinite_raises_in_betting_round(self):
        """
        Tests that a betting round with multiple raises terminates correctly
        when a player is all-in, preventing an infinite re-raise loop.
        """
        # STATE: Post-flop (street 1), 2 players.
        street = 1
        active_players = np.array([True, True])
        
        # SCENARIO: P0 bets, P1 raises, P0 re-raises, P1 goes all-in, P0 calls.
        history = "brrrc" 
        player_stacks = np.array([0.0, 0.0]) # Both players are all-in.
        bets = np.array([200.0, 200.0]) # Bets are equal.
        num_actions_this_street = 5

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)

        self.assertTrue(is_over, "The round should terminate after an all-in re-raise sequence is called.")

    def test_bet_raise_call_termination(self):
        """
        Tests if a betting round terminates after a bet, a raise, and a call.
        This is a critical scenario that can cause loops if not handled correctly.
        """
        # STATE: Post-flop (street 1), 2 players.
        street = 1
        active_players = np.array([True, True])
        player_stacks = np.array([150.0, 150.0])
        
        # SCENARIO: P0 bets, P1 raises, P0 calls.
        history = "brc"
        bets = np.array([40.0, 40.0]) # P0 calls P1's raise, so bets are equal.
        num_actions_this_street = 3

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)

        self.assertTrue(is_over, "The round should end after a bet, raise, and call sequence.")

    def test_cfr_recursive_terminates_when_no_player_can_act(self):
        """
        Ensures that _cfr_recursive terminates if no player can act,
        even if _is_betting_round_over returns False. This is a critical
        safeguard against infinite loops.
        """
        player_hands = [['Ah', 'Ad'], ['Ks', 'Kd']]
        board = []
        pot = 200.0
        bets = np.array([100.0, 100.0])
        reach_probs = np.ones(2)
        active_players = np.array([True, True])
        # All players are all-in, so no one can act.
        player_stacks = np.array([0.0, 0.0])
        street = 1
        num_actions_this_street = 2

        # We mock _is_betting_round_over to return False to simulate a faulty state
        # that could cause an infinite loop.
        with patch.object(self.trainer, '_is_betting_round_over', return_value=False):
            # The recursion should terminate and move to the next street or end the hand.
            # We expect _get_terminal_utility to be called because the game should advance.
            with patch.object(self.trainer, '_get_terminal_utility') as mock_get_utility:
                mock_get_utility.return_value = np.zeros(self.trainer.num_players)
                
                self.trainer._cfr_recursive(
                    player_hands, "rc", board, pot, bets, reach_probs,
                    active_players, player_stacks, street, num_actions_this_street,
                    recursion_depth=0
                )

                # The game should have transitioned to a terminal state.
                mock_get_utility.assert_called()
                # The recursion should not have gone deeper.
                self.assertEqual(self.trainer.recursion_depth, 0, "Recursion should not deepen if no player can act.")

    def test_preflop_3bet_scenario_termination(self):
        """
        Tests if a pre-flop 3-bet scenario terminates correctly after the
        initial raiser calls the 3-bet, which is a common source of loops.
        """
        self.trainer.num_players = 3
        street = 0
        active_players = np.array([False, True, True]) # SB folded
        player_stacks = np.array([199.0, 182.0, 182.0])

        # SCENARIO: BTN raises, SB folds, BB 3-bets, BTN calls.
        history = "rfrc"
        bets = np.array([1.0, 18.0, 18.0]) # SB folded, BB and BTN have equal bets.
        num_actions_this_street = 4

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)

        self.assertTrue(is_over, "The pre-flop 3-bet round should terminate after the initial raiser calls.")

    def test_street_transition_after_betting_round(self):
        """
        Tests that the game correctly transitions to the next street after a
        betting round concludes, which is a critical point for recursion errors.
        """
        player_hands = [['Ah', 'Ad'], ['Ks', 'Kd']]
        board = ['2h', '3h', '4h'] # Flop
        pot = 6.0
        bets = np.array([0.0, 0.0])
        reach_probs = np.ones(2)
        active_players = np.array([True, True])
        player_stacks = np.array([197.0, 197.0])
        street = 1 # Post-flop

        # SCENARIO: A simple check-check on the flop.
        history = "kk"
        num_actions_this_street = 2

        # We expect _handle_new_street to be called once to move to the turn.
        with patch.object(self.trainer, '_handle_new_street') as mock_handle_street:
            mock_handle_street.return_value = np.zeros(self.trainer.num_players)
            self.trainer._cfr_recursive(
                player_hands, history, board, pot, bets, reach_probs,
                active_players, player_stacks, street, num_actions_this_street,
                recursion_depth=0
            )
            # The game should have transitioned to the next street exactly once.
            mock_handle_street.assert_called_once()

    def test_multi_way_pot_with_calls(self):
        """
        Tests if a multi-way pot with multiple callers terminates correctly.
        """
        self.trainer.num_players = 3
        street = 1 # Post-flop
        active_players = np.array([True, True, True])
        player_stacks = np.array([180.0, 180.0, 180.0])

        # SCENARIO: P0 bets, P1 calls, P2 calls.
        history = "bcc"
        bets = np.array([20.0, 20.0, 20.0])
        num_actions_this_street = 3

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        self.assertTrue(is_over, "A multi-way pot with a bet and two calls should terminate the round.")

    def test_betting_round_reopened_after_check(self):
        """
        Tests that a player who checks can act again if another player bets in the same round.
        """
        self.trainer.num_players = 3
        street = 1 # Post-flop
        active_players = np.array([True, True, True])
        player_stacks = np.array([200.0, 200.0, 200.0])

        # SCENARIO: P0 checks, P1 bets, P2 folds. Action is back on P0. The round is NOT over.
        history = "kbf"
        bets = np.array([0.0, 20.0, 0.0])
        active_players[2] = False
        num_actions_this_street = 3

        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        self.assertFalse(is_over, "Round should not be over when a check is followed by a bet.")

        # SCENARIO CONTINUED: P0 calls. Now the round should be over.
        history = "kbfc"
        bets[0] = 20.0
        num_actions_this_street = 4

        is_over_after_call = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        self.assertTrue(is_over_after_call, "Round should be over after the checker calls the bet.")

    def test_side_pot_scenario_termination(self):
        """
        Tests a complex multi-way all-in scenario that creates a side pot.
        """
        self.trainer.num_players = 4
        street = 1 # Post-flop
        # P0 is deep-stacked, P1 is all-in, P2 is short-stacked all-in, P3 has a medium stack.
        active_players = np.array([True, True, True, True])
        player_stacks = np.array([300.0, 0.0, 0.0, 150.0])
        
        # SCENARIO: P0 bets 100, P1 calls all-in for 50, P2 calls all-in for 20, P3 calls 100.
        # The bets array reflects the total amount committed by each player in the hand.
        bets = np.array([100.0, 50.0, 20.0, 100.0])
        history = "bccc" # Simplified history for state representation
        num_actions_this_street = 4

        # Even though bets are unequal, the round should be over because the players with remaining stacks
        # have matched the highest bet, and the other players are all-in.
        is_over = self.trainer._is_betting_round_over(history, bets, active_players, street, num_actions_this_street, player_stacks)
        self.assertTrue(is_over, "The betting round with a side pot should terminate correctly.")

    def test_walk_preflop(self):
        """
        Tests if the hand terminates correctly when everyone folds to the Big Blind pre-flop.
        """
        self.trainer.num_players = 3
        street = 0
        # P0 (BTN) folds, P1 (SB) folds. P2 (BB) wins.
        active_players = np.array([False, False, True])
        player_stacks = np.array([200.0, 199.0, 198.0])
        bets = np.array([0.0, 1.0, 2.0])
        history = "ff"
        num_actions_this_street = 2

        # The betting round isn't technically "over" in the traditional sense,
        # but the hand should proceed to a terminal state (showdown with one player).
        # We'll test this by checking if _cfr_recursive correctly identifies this
        # as a situation that doesn't require further betting actions.
        with patch.object(self.trainer, '_get_terminal_utility') as mock_get_utility:
            mock_get_utility.return_value = np.zeros(self.trainer.num_players)
            
            self.trainer._cfr_recursive(
                player_hands=[[], [], []], history=history, board=[], pot=3.0, bets=bets,
                reach_probs=np.ones(3), active_players=active_players,
                player_stacks=player_stacks, street=street,
                num_actions_this_street=num_actions_this_street, recursion_depth=0
            )
            
            # The hand should end, and utility should be calculated.
            mock_get_utility.assert_called_once()

if __name__ == '__main__':
    unittest.main()
