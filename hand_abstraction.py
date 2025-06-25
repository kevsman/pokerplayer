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
        self._bucket_cache = {}  # Add a cache for hand bucketing

    def bucket_hand(self, player_hole_cards, community_cards, stage, num_opponents=1):
        """
        Buckets the hand based on its equity (win probability) against the actual number of opponents.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not player_hole_cards or len(player_hole_cards) != 2:
            return 0
        # Use a tuple of all relevant info as the cache key
        cache_key = (tuple(player_hole_cards), tuple(community_cards), stage, num_opponents)
        if cache_key in self._bucket_cache:
            logger.debug(f"Cache hit for hand bucketing")
            return self._bucket_cache[cache_key]
        
        logger.debug(f"Computing hand bucket for {player_hole_cards} with {len(community_cards)} community cards")
        # Use a very low number of simulations for debugging
        win_prob, _, _ = self.equity_calculator.calculate_equity_monte_carlo(
            [player_hole_cards],
            community_cards,
            None,
            5,   # Only 5 simulations for debugging
            num_opponents
        )
        logger.debug(f"Hand bucket calculation complete, win_prob={win_prob}")
        for i, bucket_ceiling in enumerate(self.equity_buckets):
            if win_prob <= bucket_ceiling:
                self._bucket_cache[cache_key] = i
                return i
        self._bucket_cache[cache_key] = len(self.equity_buckets) - 1
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
