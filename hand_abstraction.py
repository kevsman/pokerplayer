"""
Hand abstraction module for PokerBotV2.
Implements hand and board bucketing for abstraction.
"""
from equity_calculator import EquityCalculator
from hand_evaluator import HandEvaluator

class HandAbstraction:
    def __init__(self, hand_evaluator: HandEvaluator, equity_calculator: EquityCalculator):
        self.hand_evaluator = hand_evaluator
        self.equity_calculator = equity_calculator
        # Buckets based on equity ranges: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%
        self.equity_buckets = [0.2, 0.4, 0.6, 0.8, 1.0]

    def bucket_hand(self, player_hole_cards, community_cards, stage):
        """
        Buckets the hand based on its equity (win probability) against a single random opponent.
        """
        if not player_hole_cards:
            return 0

        # Use a fast Monte Carlo simulation to estimate equity
        win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
            [player_hole_cards],
            community_cards,
            num_opponents=1,
            num_simulations=500  # Lower simulations for speed during real-time decision
        )

        # Find which bucket the win probability falls into
        for i, bucket_threshold in enumerate(self.equity_buckets):
            if win_prob <= bucket_threshold:
                return i
        return len(self.equity_buckets) - 1

    def bucket_board(self, community_cards, stage):
        """
        Buckets the board based on its texture.
        - 0: Preflop (no board)
        - 1: Paired and Monotone/Flush-Heavy
        - 2: Paired
        - 3: Monotone/Flush-Heavy
        - 4: Two-Tone/Some Flush Draw
        - 5: Dry/Rainbow
        """
        if not community_cards or stage == 'preflop':
            return 0

        ranks = [c[:-1] for c in community_cards]
        suits = [c[-1] for c in community_cards]

        is_paired = len(set(ranks)) < len(ranks)
        
        suit_counts = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        
        is_monotone = any(c >= 3 for c in suit_counts.values())
        is_two_tone = any(c == 2 for c in suit_counts.values())

        if is_paired and is_monotone:
            return 1
        if is_paired:
            return 2
        if is_monotone:
            return 3
        if is_two_tone:
            return 4
        
        return 5  # Dry board
