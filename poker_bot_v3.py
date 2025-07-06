#!/usr/bin/env python3
"""
Poker Bot v3: Low-Stakes Cash Game Specialist

This file contains the implementation of a rule-based poker bot optimized for 
low-stakes No-Limit Hold'em cash games (2-6 players).

The strategy is based on an exploitative, tight-aggressive (TAG) style, 
focusing on strong hand selection, positional advantage, and value betting.
"""

import random
from itertools import combinations
import logging
import sys
import time
from ui_controller import UIController
from html_parser import PokerPageParser
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

# --- Setup Logging ---
# Create both console and file logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Remove any existing handlers to prevent duplication
for handler in logger.handlers[:]:
    handler.close()
    logger.removeHandler(handler)

# File handler for detailed logging
log_file_path = 'poker_bot_v3.log'
fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
fh.setLevel(logging.DEBUG)

# Console handler for real-time feedback
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# Configure formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(fh)
logger.addHandler(ch)
logger.propagate = False

# --- Constants ---
RANKS = '23456789TJQKA'
SUITS = 'hdcs'
RANK_MAP = {rank: i for i, rank in enumerate(RANKS)}

class HandEvaluator:
    """Evaluates the strength of a poker hand."""
    def evaluate_hand(self, hand, board):
        """
        Evaluates the best 5-card hand from 2 hole cards and 3-5 community cards.
        Returns a numeric score (higher is better) and a string description.
        """
        all_cards = hand + board
        if len(all_cards) < 5:
            return 0, "Not enough cards"

        best_score = (0,)  # Initialize as tuple to match the return type
        best_hand_name = ""

        for combo in combinations(all_cards, 5):
            score, name = self._evaluate_5_card_hand(list(combo))
            if score > best_score:
                best_score = score
                best_hand_name = name
        
        return best_score, best_hand_name

    def _evaluate_5_card_hand(self, hand):
        """
        Evaluates a 5-card hand and returns a score and name.
        """
        ranks = sorted([RANK_MAP[c.rank] for c in hand], reverse=True)
        suits = [c.suit for c in hand]
        
        is_flush = len(set(suits)) == 1
        
        # Check for straight
        is_straight = all(ranks[i] - ranks[i+1] == 1 for i in range(len(ranks)-1))
        # Ace-low straight (A, 2, 3, 4, 5)
        if not is_straight and ranks == [12, 3, 2, 1, 0]: # A, 5, 4, 3, 2
             ranks = [3, 2, 1, 0, -1] # Treat Ace as low for scoring
             is_straight = True

        # Hand strength scoring
        # The score is a tuple, allowing for comparison of hands of the same rank
        # e.g., (8, 12) for Straight Flush to the Ace (Royal Flush)
        # e.g., (1, 12, [10, 9, 8]) for Pair of Aces with K, Q, J kickers
        
        rank_counts = {r: ranks.count(r) for r in ranks}
        counts = sorted(rank_counts.values(), reverse=True)
        major_ranks = sorted([r for r, c in rank_counts.items() if c > 1], reverse=True)

        if is_straight and is_flush:
            return (8, ranks[0]), "Straight Flush"
        if counts[0] == 4:
            return (7, major_ranks[0], [r for r in ranks if r != major_ranks[0]][0]), "Four of a Kind"
        if counts == [3, 2]:
            return (6, major_ranks[0], major_ranks[1]), "Full House"
        if is_flush:
            return (5, tuple(ranks)), "Flush"
        if is_straight:
            return (4, ranks[0]), "Straight"
        if counts[0] == 3:
            kickers = sorted([r for r in ranks if r != major_ranks[0]], reverse=True)
            return (3, major_ranks[0], tuple(kickers)), "Three of a Kind"
        if counts == [2, 2, 1]:
            kickers = [r for r in ranks if r not in major_ranks]
            return (2, tuple(major_ranks), kickers[0]), "Two Pair"
        if counts[0] == 2:
            kickers = sorted([r for r in ranks if r != major_ranks[0]], reverse=True)
            return (1, major_ranks[0], tuple(kickers)), "One Pair"
        
        return (0, tuple(ranks)), "High Card"

class Card:
    """Represents a single playing card."""
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __repr__(self):
        return f"{self.rank}{self.suit}"


class PokerBotV3:
    """A rule-based bot for low-stakes cash games."""
    def __init__(self):
        self.position = None
        self.num_players = 0
        self.hand = []
        self.evaluator = HandEvaluator()

    def get_preflop_action(self, hand, position, num_players, bet_to_call=0, pot_size=0):
        """Determines the pre-flop action based on hand strength and position."""
        self.position = position
        self.num_players = num_players

        # TAG Strategy: Tight-Aggressive pre-flop charts
        raise_charts = {
            'early': ['AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AKo', 'AQs', 'AQo'],
            'middle': ['99', '88', 'AJs', 'ATs', 'KQs', 'AJo', 'ATo', 'KQo'],
            'late': ['77', '66', '55', 'A9s', 'A8s', 'A7s', 'KTs', 'QJs', 'JTs', 'T9s', '98s'],
            'sb': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', 'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'ATs'],
            'bb': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', 'AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'ATs', 'KQs']
        }

        # Calling ranges - hands good enough to call but not raise
        call_charts = {
            'early': ['99', '88'],
            'middle': ['77', '66', 'A9s'],
            'late': ['55', '44', '33', '22', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s', 'K9s', 'Q9s', 'J9s', '87s', '76s', '65s'],
            'sb': ['77', '66', '55', '44', '33', '22', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s', 'K9s', 'KTs', 'KJs', 'Q9s', 'QTs', 'J9s', 'JTs', 'T8s', '98s', '87s', '76s', '65s', '54s'],
            'bb': ['77', '66', '55', '44', '33', '22', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s', 'K9s', 'K8s', 'K7s', 'K6s', 'Q9s', 'Q8s', 'J9s', 'J8s', 'T8s', '98s', '87s', '76s', '65s', '54s', 'K9o', 'KTo', 'QTo', 'JTo']
        }

        # Combine all raise charts (higher positions include lower position hands)
        raise_charts['middle'] = list(set(raise_charts['middle'] + raise_charts['early']))
        raise_charts['late'] = list(set(raise_charts['late'] + raise_charts['middle']))

        position_map = {
            'UTG': 'early', 'MP': 'middle',
            'CO': 'late', 'BTN': 'late',
            'SB': 'sb', 'BB': 'bb'
        }
        pos_category = position_map.get(self.position, 'middle')

        hand_str = self._get_hand_string(hand)
        
        logger.info(f"Preflop analysis: Hand={hand_str}, Position={position}, Category={pos_category}, BetToCall={bet_to_call}")

        # Special case: Big Blind with no raise (can check for free)
        if position == 'BB' and bet_to_call <= 0.01:
            logger.info("Big blind with no raise - checking for free")
            return 'CHECK', 0
        
        # Check if we should raise with this hand
        if hand_str in raise_charts.get(pos_category, []):
            # Calculate proper raise size based on action
            raise_amount = self._calculate_preflop_raise_size(bet_to_call, pot_size, hand_str)
            logger.info(f"Hand {hand_str} is in raise range for {pos_category} - raising to {raise_amount}")
            return 'RAISE', raise_amount
        
        # Check if we should call with this hand
        if hand_str in call_charts.get(pos_category, []):
            # Only call if there's a reasonable bet to call
            if bet_to_call > 0.01:
                # Check if bet size is reasonable for calling
                max_call_size = self._calculate_max_preflop_call_size(hand_str, pot_size, position)
                if bet_to_call <= max_call_size:
                    logger.info(f"Hand {hand_str} is in call range for {pos_category} - calling bet of {bet_to_call} (max: {max_call_size})")
                    return 'CALL', bet_to_call
                else:
                    logger.info(f"Hand {hand_str} in call range but bet {bet_to_call} too large (max: {max_call_size}) - folding")
                    return 'FOLD', 0
            elif position == 'SB':  # Small blind completing
                # Small blind completing to big blind
                sb_complete_amount = max(bet_to_call, 0.01)  # At least complete to BB
                logger.info(f"Small blind completing with {hand_str} for {sb_complete_amount}")
                return 'CALL', sb_complete_amount
        
        # Special handling for big blind with expanded calling range
        if position == 'BB' and bet_to_call > 0.01:
            # Big blind gets good pot odds, so wider calling range
            bb_defense_hands = ['A2o', 'A3o', 'A4o', 'A5o', 'A6o', 'A7o', 'A8o', 'A9o', 'K2s', 'K3s', 'K4s', 'K5s']
            if hand_str in bb_defense_hands:
                # Check if bet size is reasonable for defending
                max_call_size = self._calculate_max_preflop_call_size(hand_str, pot_size, position)
                if bet_to_call <= max_call_size:
                    logger.info(f"Big blind defending with {hand_str} against bet of {bet_to_call} (max: {max_call_size})")
                    return 'CALL', bet_to_call
                else:
                    logger.info(f"Big blind defense hand {hand_str} but bet {bet_to_call} too large (max: {max_call_size}) - folding")
                    return 'FOLD', 0

        # Default action: fold
        logger.info(f"Hand {hand_str} not in range for {pos_category} - folding")
        return 'FOLD', 0

    def _get_hand_string(self, hand):
        """Converts a hand (list of Card objects) to a string like 'AKs' or '77'"""
        card1, card2 = hand[0], hand[1]
        r1_val = RANK_MAP[card1.rank]
        r2_val = RANK_MAP[card2.rank]

        if r1_val < r2_val:
            card1, card2 = card2, card1 # Ensure card1 is the higher rank

        hand_str = f"{card1.rank}{card2.rank}"
        if card1.rank == card2.rank:
            return hand_str # Pocket pair, e.g., '77'
        
        if card1.suit == card2.suit:
            return f"{hand_str}s" # Suited, e.g., 'AKs'
        else:
            return f"{hand_str}o" # Off-suit, e.g., 'AQo'

    def get_postflop_action(self, hand, board, pot_size, bet_to_call):
        """Determines post-flop action based on hand strength, board texture, and game state."""
        hand_score, hand_name = self.evaluator.evaluate_hand(hand, board)
        hand_rank = hand_score[0] if isinstance(hand_score, tuple) else hand_score  # Handle both tuple and int

        logger.info(f"--- Post-flop Decision ---")
        logger.info(f"Board: {[str(card) for card in board]}")
        logger.info(f"Bot's best hand: {hand_name} (Score: {hand_rank})")
        logger.info(f"Pot size: {pot_size}, Bet to call: {bet_to_call}")

        # --- Basic Pot Odds Calculation ---
        pot_odds = 0
        implied_pot_odds = 0
        if bet_to_call > 0:
            pot_odds = bet_to_call / (pot_size + bet_to_call)
            implied_pot_odds = bet_to_call / (pot_size + bet_to_call + pot_size * 0.5)  # Assume additional 50% pot betting
            logger.info(f"Pot odds: {pot_odds:.2f}, Implied odds: {implied_pot_odds:.2f}")

        # Analyze board texture for decision making
        board_texture = self._analyze_board_texture(board)
        logger.info(f"Board texture: {board_texture}")

        # --- Hand Strength Tiers & Aggressive TAG Decision Logic ---

        # Tier 1: Monster Hand (Full House or better) - 8, 7, 6
        # Goal: Extract maximum value
        if hand_rank >= 6:
            logger.info("Monster hand detected - extracting value")
            if bet_to_call > 0:
                # Always raise for value with monsters
                raise_amount = self._calculate_postflop_raise_size(bet_to_call, pot_size, 'monster')
                return 'RAISE', raise_amount
            else:
                # Bet for value when checked to
                bet_amount = self._calculate_postflop_bet_size(pot_size, 'monster')
                return 'BET', bet_amount

        # Tier 2: Very Strong Hand (Flush, Straight) - 5, 4
        # Goal: Build pot aggressively, but watch for scary runouts
        elif hand_rank >= 4:
            logger.info("Very strong hand - betting for value")
            if bet_to_call > 0:
                # Call or raise depending on bet size
                if pot_odds < 0.4:  # Call normal bets
                    return 'CALL', bet_to_call
                else:  # Fold to huge overbets only
                    if hand_rank == 5:  # Flush - more willing to call
                        return 'CALL', bet_to_call
                    else:  # Straight - fold to huge bets on paired/flush boards
                        return 'FOLD', 0
            else:
                # Bet for value
                bet_amount = self._calculate_postflop_bet_size(pot_size, 'strong')
                return 'BET', bet_amount

        # Tier 3: Strong Hand (Three of a Kind, Two Pair) - 3, 2
        # Goal: Extract value but be cautious on dangerous boards
        elif hand_rank >= 2:
            logger.info("Strong hand - seeking value with caution")
            if bet_to_call > 0:
                if hand_rank == 3:  # Three of a kind
                    if pot_odds < 0.5:  # Very willing to call with trips
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
                else:  # Two pair
                    if pot_odds < 0.3:  # More cautious with two pair
                        return 'CALL', bet_to_call
                    elif board_texture['is_dry']:  # More willing on dry boards
                        if pot_odds < 0.4:
                            return 'CALL', bet_to_call
                        else:
                            return 'FOLD', 0
                    else:
                        return 'FOLD', 0
            else:
                # Bet for value, especially on dry boards
                if board_texture['is_dry'] or hand_rank == 3:
                    bet_amount = self._calculate_postflop_bet_size(pot_size, 'medium')
                    return 'BET', bet_amount
                else:
                    return 'CHECK', 0  # Check behind on wet boards with two pair

        # Tier 4: Marginal Made Hand (One Pair) - 1
        # Goal: Pot control, selective aggression
        elif hand_rank == 1:
            # Check pair strength 
            pair_rank = hand_score[1] if isinstance(hand_score, tuple) and len(hand_score) > 1 else 10
            is_top_pair = self._is_top_pair(hand, board, pair_rank)
            is_overpair = self._is_overpair(hand, board, pair_rank)
            
            logger.info(f"One pair analysis - Top pair: {is_top_pair}, Overpair: {is_overpair}")
            
            if bet_to_call > 0:
                if is_overpair or (is_top_pair and board_texture['is_dry']):
                    # Strong one pair hands - call reasonable bets
                    if pot_odds < 0.25:
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
                elif is_top_pair:
                    # Top pair on wet boards - tighter
                    if pot_odds < 0.15:
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
                else:
                    # Weak pairs - fold to any significant bet
                    if pot_odds < 0.1:
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
            else:
                # No bet to call - decide whether to bet or check
                if is_overpair or (is_top_pair and board_texture['is_dry']):
                    bet_amount = self._calculate_postflop_bet_size(pot_size, 'small')
                    return 'BET', bet_amount  # Bet for value with strong pairs
                else:
                    return 'CHECK', 0  # Check with weaker pairs

        # Tier 5: Drawing Hands & High Card - 0
        # Goal: Check/fold cheaply, look for draws
        else:
            draws = self._analyze_draws(hand, board)
            logger.info(f"Drawing analysis: {draws}")
            
            if bet_to_call > 0:
                # Check if we have strong draws worth calling
                if draws['nut_flush_draw'] or draws['open_ended_straight']:
                    if pot_odds < 0.25:  # Good price for strong draws
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
                elif draws['flush_draw'] or draws['gutshot']:
                    if pot_odds < 0.15:  # Need good price for weaker draws
                        return 'CALL', bet_to_call
                    else:
                        return 'FOLD', 0
                else:
                    # No draws, fold to any bet
                    return 'FOLD', 0
            else:
                # No bet - always check (never fold for free)
                return 'CHECK', 0

    def _calculate_postflop_raise_size(self, bet_to_call, pot_size, hand_strength):
        """Calculate appropriate postflop raise size based on hand strength."""
        if hand_strength == 'monster':
            # Extract maximum value - larger raise
            raise_size = bet_to_call + (pot_size * 1.2)  # Call + overbet pot
            logger.info(f"Monster hand raise: calling {bet_to_call} + betting {pot_size * 1.2} = {raise_size}")
        else:
            # Standard value raise - call + reasonable raise
            raise_size = bet_to_call + (pot_size * 0.7)  # Call + 70% pot raise
            logger.info(f"Standard postflop raise: calling {bet_to_call} + betting {pot_size * 0.7} = {raise_size}")
        
        return raise_size

    def _calculate_postflop_bet_size(self, pot_size, hand_strength):
        """Calculate appropriate postflop bet size based on hand strength."""
        if hand_strength == 'monster':
            # Large value bet to extract maximum
            bet_size = pot_size * 0.85
            logger.info(f"Monster hand bet: {bet_size} ({bet_size/pot_size:.1%} pot)")
        elif hand_strength == 'strong':
            # Standard value bet
            bet_size = pot_size * 0.7
            logger.info(f"Strong hand bet: {bet_size} ({bet_size/pot_size:.1%} pot)")
        elif hand_strength == 'medium':
            # Medium value bet
            bet_size = pot_size * 0.5
            logger.info(f"Medium hand bet: {bet_size} ({bet_size/pot_size:.1%} pot)")
        else:  # small
            # Small value bet for protection/thin value
            bet_size = pot_size * 0.35
            logger.info(f"Small hand bet: {bet_size} ({bet_size/pot_size:.1%} pot)")
        
        # Ensure minimum bet size
        return max(bet_size, 0.02)  # Minimum 0.02 bet

    def _analyze_board_texture(self, board):
        """Analyze board texture for wetness, pairs, straight/flush possibilities."""
        if len(board) < 3:
            return {'is_dry': True, 'is_paired': False, 'flush_possible': False, 'straight_possible': False}
        
        ranks = [RANK_MAP[card.rank] for card in board]
        suits = [card.suit for card in board]
        
        # Check for pairs
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        is_paired = any(count >= 2 for count in rank_counts.values())
        
        # Check for flush possibilities
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        flush_possible = any(count >= 3 for count in suit_counts.values())
        
        # Check for straight possibilities (simplified)
        sorted_ranks = sorted(set(ranks))
        straight_possible = False
        if len(sorted_ranks) >= 3:
            for i in range(len(sorted_ranks) - 2):
                if sorted_ranks[i+2] - sorted_ranks[i] <= 4:  # Within 5 card range
                    straight_possible = True
                    break
        
        # Determine if board is dry (opposite of wet)
        is_dry = not (flush_possible or straight_possible or is_paired)
        
        return {
            'is_dry': is_dry,
            'is_paired': is_paired,
            'flush_possible': flush_possible,
            'straight_possible': straight_possible
        }

    def _is_top_pair(self, hand, board, pair_rank):
        """Check if we have top pair."""
        if len(board) == 0:
            return False
        
        board_ranks = [RANK_MAP[card.rank] for card in board]
        highest_board_rank = max(board_ranks)
        
        # Check if our pair rank matches the highest board rank
        return pair_rank == highest_board_rank

    def _is_overpair(self, hand, board, pair_rank):
        """Check if we have an overpair."""
        if len(board) == 0:
            return False
        
        board_ranks = [RANK_MAP[card.rank] for card in board]
        highest_board_rank = max(board_ranks)
        
        # Check if our pair rank is higher than the highest board rank
        return pair_rank > highest_board_rank

    def _analyze_draws(self, hand, board):
        """Analyze potential draws."""
        if len(board) < 3 or len(hand) != 2:
            return {'nut_flush_draw': False, 'flush_draw': False, 'open_ended_straight': False, 'gutshot': False}
        
        all_cards = hand + board
        ranks = [RANK_MAP[card.rank] for card in all_cards]
        suits = [card.suit for card in all_cards]
        
        # Flush draw analysis
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        flush_draw = any(count == 4 for count in suit_counts.values())
        
        # Check if it's a nut flush draw (need ace of the flush suit)
        nut_flush_draw = False
        if flush_draw:
            flush_suit = [suit for suit, count in suit_counts.items() if count == 4][0]
            hand_suits = [card.suit for card in hand]
            hand_ranks = [card.rank for card in hand]
            if flush_suit in hand_suits:
                # Check if we have ace of the flush suit
                for i, card in enumerate(hand):
                    if card.suit == flush_suit and card.rank == 'A':
                        nut_flush_draw = True
                        break
        
        # Straight draw analysis (simplified)
        unique_ranks = sorted(set(ranks))
        open_ended_straight = False
        gutshot = False
        
        # This is a simplified straight draw detection
        # In a real implementation, you'd want more sophisticated logic
        if len(unique_ranks) >= 4:
            # Check for potential straights
            for i in range(len(unique_ranks) - 3):
                consecutive = unique_ranks[i:i+4]
                if consecutive[-1] - consecutive[0] == 3:  # 4 consecutive ranks
                    # Could be open-ended or gutshot
                    if i == 0 or i == len(unique_ranks) - 4:
                        open_ended_straight = True
                    else:
                        gutshot = True
        
        return {
            'nut_flush_draw': nut_flush_draw,
            'flush_draw': flush_draw,
            'open_ended_straight': open_ended_straight,
            'gutshot': gutshot
        }

    def _calculate_preflop_raise_size(self, bet_to_call, pot_size, hand_str):
        """Calculate appropriate preflop raise size based on action and hand strength."""
        # Standard preflop raise sizing for low-stakes cash games
        
        # If it's an opening raise (no one has bet before us)
        if bet_to_call <= 0.01:
            # Standard opening raise: 3x big blind
            # Since we don't have access to BB size, use pot-based sizing
            return max(pot_size * 0.5, 0.06)  # Min raise of 0.06 for safety
        
        # If facing a bet (3-betting)
        else:
            # Premium hands (AA, KK, QQ, AK) - larger 3-bet
            premium_hands = ['AA', 'KK', 'QQ', 'AKs', 'AKo']
            
            if hand_str in premium_hands:
                # Aggressive 3-bet sizing: 3-4x the original bet
                raise_size = bet_to_call * 3.5
                logger.info(f"Premium hand {hand_str}: 3-betting {bet_to_call} to {raise_size}")
                return raise_size
            else:
                # Standard 3-bet sizing: 3x the original bet
                raise_size = bet_to_call * 3.0
                logger.info(f"Standard 3-bet with {hand_str}: raising {bet_to_call} to {raise_size}")
                return raise_size

    def _calculate_max_preflop_call_size(self, hand_str, pot_size, position):
        """Calculate maximum bet size we're willing to call preflop based on hand strength."""
        
        # Hand strength tiers for calling
        premium_calling_hands = ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo', 'AQs', 'AQo']
        strong_calling_hands = ['TT', '99', '88', 'AJs', 'ATs', 'AJo', 'ATo', 'KQs', 'KQo', 'QJs', 'JTs']
        medium_calling_hands = ['77', '66', '55', 'A9s', 'A8s', 'A7s', 'KTs', 'K9s', 'QTs', 'Q9s', 'J9s', 'T9s', '98s', '87s']
        weak_calling_hands = ['44', '33', '22', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s', 'K8s', 'K7s', 'K6s', 'Q8s', 'J8s', 'T8s', '97s', '76s', '65s', '54s']
        
        # Base maximum call size as multiple of pot
        base_pot_multiple = 0.5  # Conservative default
        
        if hand_str in premium_calling_hands:
            # Premium hands can call larger bets
            base_pot_multiple = 2.0  # Can call up to 2x pot
            if position in ['BB']:
                base_pot_multiple = 2.5  # BB gets better odds, can call more
        elif hand_str in strong_calling_hands:
            # Strong hands - moderate calling
            base_pot_multiple = 1.2
            if position in ['BB']:
                base_pot_multiple = 1.5
        elif hand_str in medium_calling_hands:
            # Medium hands - tight calling
            base_pot_multiple = 0.8
            if position in ['BB']:
                base_pot_multiple = 1.0
        elif hand_str in weak_calling_hands:
            # Weak hands - very tight calling
            base_pot_multiple = 0.4
            if position in ['BB']:
                base_pot_multiple = 0.6
        else:
            # Not in any calling range - very small calls only
            base_pot_multiple = 0.2
        
        max_call = pot_size * base_pot_multiple
        
        # Ensure minimum and maximum bounds
        max_call = max(max_call, 0.02)  # Minimum call of 0.02
        max_call = min(max_call, pot_size * 3.0)  # Never call more than 3x pot preflop
        
        logger.debug(f"Max call size for {hand_str} in {position}: {max_call} ({base_pot_multiple}x pot of {pot_size})")
        return max_call

class PokerBotV3Manager:
    """Manager class that handles the parsing and analysis like poker_bot_v2."""
    def __init__(self):
        self.parser = PokerPageParser()
        self.ui_controller = UIController()
        self.table_data = {}
        self.player_data = []
        self.last_html_content = None

    def analyze_table(self):
        self.table_data = self.parser.analyze_table()

    def analyze_players(self):
        self.player_data = self.parser.analyze_players()

    def get_active_player(self):
        for player in self.player_data:
            if player.get('has_turn', False):
                return player
        return None
        
    def get_my_player(self):
        for player in self.player_data:
            if player.get('is_my_player', False):
                return player
        return None

    def analyze(self):
        self.analyze_table() 
        self.analyze_players() 
        return {
            'table': self.table_data,
            'players': self.player_data,
            'my_player': self.get_my_player(),
            'active_player': self.get_active_player()
        }

def main():
    """Main loop for the poker bot."""
    logger.info("🚀 ============================================")
    logger.info("🚀 POKER BOT V3 - LOW-STAKES CASH GAME SPECIALIST")
    logger.info("🚀 ============================================")
    logger.info("🎯 Strategy: Rule-based Tight-Aggressive (TAG)")
    logger.info("🎯 Target: Low-stakes 2-6 player cash games")
    logger.info("🚀 Starting main loop...")
    
    manager = PokerBotV3Manager()
    bot = PokerBotV3()
    
    # Check if UI positions are calibrated (like poker_bot_v2)
    if not manager.ui_controller.positions:
        logger.warning("⚠️  UI positions not calibrated. Please run calibration first.")
        logger.info("💡 Run: python ui_controller.py to calibrate positions")
        return

    logger.info("✅ UI positions calibrated. Bot ready for action!")
    logger.info("🎯 Press Ctrl+C to stop the bot")
    logger.info("📝 All decisions will be logged to poker_bot_v3.log")

    try:
        while True:
            logger.info("\n--- 🎲 New Decision Cycle ---")
            
            # 1. Capture HTML from the poker client
            html = manager.ui_controller.get_html_from_screen_with_auto_retry()

            if not html:
                logger.info("No HTML content captured. Waiting...")
                time.sleep(2)
                continue

            # 2. Parse the game state using the same approach as poker_bot_v2
            manager.last_html_content = html
            parsed_state = manager.parser.parse_html(html)
            
            if not parsed_state or parsed_state.get('error'):
                logger.error(f"Failed to parse HTML: {parsed_state.get('error', 'Unknown') if parsed_state else 'None'}. Retrying...")
                time.sleep(1)
                continue

            # 3. Analyze the game state
            game_state = manager.analyze()
            my_player = game_state.get('my_player')
            
            # 4. Check if it's our turn
            if my_player and my_player.get('has_turn'):
                logger.info("🎯 It's PokerBotV3's turn to act!")
                
                # Log the hand we're holding
                player_hole_cards = my_player.get('cards', [])
                if player_hole_cards:
                    cards_str = ', '.join(player_hole_cards)
                    logger.info(f"🃏 My Hand: {cards_str}")
                else:
                    logger.warning("⚠️  No hole cards detected!")
                
                # Convert string cards to Card objects
                hand = []
                if player_hole_cards:
                    for card_str in player_hole_cards:
                        # Handle card parsing - extract rank and suit
                        if len(card_str) >= 2:
                            if card_str.startswith('10'):  # Handle '10♠' format
                                rank = 'T'  # Convert '10' to 'T'
                                suit = card_str[2:3].lower()  # Get suit character after '10'
                            else:  # Handle single character ranks like 'A♠', 'K♠', etc.
                                rank = card_str[0]
                                suit = card_str[1:2].lower()  # Get suit character
                            
                            # Normalize suit characters (remove unicode symbols)
                            suit_map = {'♠': 's', '♥': 'h', '♦': 'd', '♣': 'c', 
                                       's': 's', 'h': 'h', 'd': 'd', 'c': 'c'}
                            suit = suit_map.get(suit, suit)
                            
                            hand.append(Card(suit, rank))
                        else:
                            logger.warning(f"Could not parse card: {card_str}")
                
                community_cards_str = manager.table_data.get('community_cards', [])
                board = []
                if community_cards_str:
                    for card_str in community_cards_str:
                        # Handle card parsing - extract rank and suit
                        if len(card_str) >= 2:
                            if card_str.startswith('10'):  # Handle '10♠' format
                                rank = 'T'  # Convert '10' to 'T'
                                suit = card_str[2:3].lower()  # Get suit character after '10'
                            else:  # Handle single character ranks like 'A♠', 'K♠', etc.
                                rank = card_str[0]
                                suit = card_str[1:2].lower()  # Get suit character
                            
                            # Normalize suit characters (remove unicode symbols)
                            suit_map = {'♠': 's', '♥': 'h', '♦': 'd', '♣': 'c', 
                                       's': 's', 'h': 'h', 'd': 'd', 'c': 'c'}
                            suit = suit_map.get(suit, suit)
                            
                            board.append(Card(suit, rank))
                        else:
                            logger.warning(f"Could not parse card: {card_str}")
                
                if community_cards_str:
                    community_str = ', '.join(community_cards_str)
                    logger.info(f"🃏 Community Cards: {community_str}")

                # Get position and player count
                position = my_player.get('position', 'BTN') 
                num_players = len(manager.player_data)
                
                # Log game stage
                stage_name = manager.table_data.get('game_stage', 'preflop').lower()
                logger.info(f"📊 Game Stage: {stage_name.title()}")

                action = 'FOLD' # Default action
                amount = 0
                
                # Get bet_to_call for both preflop and postflop
                bet_to_call = my_player.get('bet_to_call', 0)
                if isinstance(bet_to_call, str):
                    bet_to_call = float(bet_to_call.replace('€', '').replace('$', '').replace(',', '').strip())
                
                # If bet_to_call is 0 or very small, it means we can check
                if bet_to_call <= 0.01:  # Account for rounding errors
                    bet_to_call = 0
                
                if len(board) == 0: # Pre-flop
                    if bet_to_call == 0:
                        logger.info(f"💡 Preflop: No bet to call - checking/limping is available")
                    else:
                        logger.info(f"💰 Preflop: Bet to call: {bet_to_call}")
                    
                    # Get pot size for preflop calculations
                    pot_size = manager.table_data.get('pot_size', 0)
                    if isinstance(pot_size, str):
                        pot_size = float(pot_size.replace('€', '').replace('$', '').replace(',', '').strip())
                    
                    action, amount = bot.get_preflop_action(hand, position, num_players, bet_to_call, pot_size)
                    logger.info(f"🎯 Pre-flop decision: {action}")
                    if amount > 0:
                        logger.info(f"💰 Raise amount: {amount}")
                else: # Post-flop
                    pot_size = manager.table_data.get('pot_size', 0)
                    # Parse currency string to get numeric value
                    if isinstance(pot_size, str):
                        pot_size = float(pot_size.replace('€', '').replace('$', '').replace(',', '').strip())
                    
                    if bet_to_call == 0:
                        logger.info(f"💡 No bet to call - checking is available")
                    else:
                        logger.info(f"💰 Bet to call: {bet_to_call}")
                    
                    action, amount = bot.get_postflop_action(hand, board, pot_size, bet_to_call)
                    logger.info(f"🎯 Post-flop decision: {action}")
                    if amount > 0:
                        logger.info(f"💰 Bet/Raise amount: {amount}")
                
                # Execute the action using UI controller (like poker_bot_v2)
                if action:
                    # Log detailed decision information
                    logger.info(f"🎮 DECISION SUMMARY:")
                    logger.info(f"   📊 Game Stage: {stage_name.title()}")
                    logger.info(f"   🃏 Hand: {cards_str}")
                    logger.info(f"   📍 Position: {position} ({num_players} players)")
                    if len(board) > 0:
                        logger.info(f"   🃏 Board: {', '.join(community_cards_str)}")
                        pot_size = manager.table_data.get('pot_size', 0)
                        if isinstance(pot_size, str):
                            pot_size = float(pot_size.replace('€', '').replace('$', '').replace(',', '').strip())
                        logger.info(f"   💰 Pot Size: {pot_size}")
                        if bet_to_call > 0:
                            logger.info(f"   💸 Bet to Call: {bet_to_call}")
                    logger.info(f"   ⚡ EXECUTING ACTION: {action}")
                    
                    if action in ['FOLD', 'Fold']:
                        manager.ui_controller.action_fold()
                    elif action in ['CHECK', 'CALL', 'Check', 'Call']:
                        if amount > 0:
                            logger.info(f"   💰 Call Amount: {amount}")
                        manager.ui_controller.action_check_call()
                    elif action in ['RAISE', 'BET', 'Raise', 'Bet']:
                        logger.info(f"   💰 Raise/Bet Amount: {amount}")
                        manager.ui_controller.action_raise(amount)
                    
                    # Wait after action like poker_bot_v2
                    logger.info(f"⏱️  Action completed. Waiting...")
                    logger.info(f"🚀 ============================================")
                    time.sleep(3)
                else:
                    logger.warning("Could not determine an action.")
            else:
                logger.info("Not my turn, or player not found. Waiting...")

            # Wait for a shorter time like poker_bot_v2
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 PokerBot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"An error occurred in the main loop: {e}", exc_info=True)
    finally:
        logger.info("🏁 PokerBot v3 main loop ended.")
        logger.info("📝 Session logged to poker_bot_v3.log")
        # Close logging handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


# --- Main Execution --- 
if __name__ == '__main__':
    main()
