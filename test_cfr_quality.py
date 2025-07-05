"""
CFR Solver Quality Test
Tests the real-time CFR solver against known good/bad scenarios to evaluate decision quality.
"""
import time
import logging
from cfr_solver import CFRSolver
from hand_abstraction import HandAbstraction
from hand_evaluator import HandEvaluator
from gpu_accelerated_equity import GPUEquityCalculator
from decision_engine import ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cfr_decision_quality():
    """Test CFR solver on various scenarios to evaluate decision quality."""
    
    # Initialize components
    hand_evaluator = HandEvaluator()
    equity_calculator = GPUEquityCalculator(use_gpu=True)
    abstraction = HandAbstraction(hand_evaluator, equity_calculator)
    cfr_solver = CFRSolver(abstraction, hand_evaluator, equity_calculator, logger)
    
    print("🧪 Testing CFR Solver Decision Quality")
    print("="*60)
    
    test_scenarios = [
        {
            'name': 'AA Preflop (Premium Hand)',
            'hole_cards': ['A♠', 'A♥'],
            'community_cards': [],
            'pot_size': 0.06,
            'stage': 'preflop',
            'expected': 'Should raise aggressively'
        },
        {
            'name': '72o Preflop (Worst Hand)',
            'hole_cards': ['7♠', '2♣'],
            'community_cards': [],
            'pot_size': 0.06,
            'stage': 'preflop',
            'expected': 'Should fold most of the time'
        },
        {
            'name': 'Set on Dry Board (Monster)',
            'hole_cards': ['8♠', '8♥'],
            'community_cards': ['8♣', '3♦', '6♠'],
            'pot_size': 0.12,
            'stage': 'flop',
            'expected': 'Should bet/raise aggressively'
        },
        {
            'name': 'Missed Draw on River',
            'hole_cards': ['A♠', '5♠'],
            'community_cards': ['K♣', '9♦', '3♥', '7♣', '2♦'],
            'pot_size': 0.80,
            'stage': 'river',
            'expected': 'Should check/fold (ace high, no pair)'
        },
        {
            'name': 'Top Pair Good Kicker',
            'hole_cards': ['A♠', 'K♥'],
            'community_cards': ['A♣', '7♦', '3♠'],
            'pot_size': 0.24,
            'stage': 'flop',
            'expected': 'Should bet for value'
        },
        {
            'name': 'Weak Pair vs Scary Board',
            'hole_cards': ['6♠', '6♥'],
            'community_cards': ['A♣', 'K♦', 'Q♠'],
            'pot_size': 0.18,
            'stage': 'flop',
            'expected': 'Should play cautiously (check/fold)'
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Hand: {scenario['hole_cards']}")
        print(f"   Board: {scenario['community_cards'] if scenario['community_cards'] else 'None'}")
        print(f"   Expected: {scenario['expected']}")
        
        # Run CFR solver multiple times to check consistency
        actions = [ACTION_FOLD, ACTION_CHECK, ACTION_CALL, ACTION_RAISE]
        
        strategies = []
        times = []
        
        for run in range(3):  # Run 3 times to check consistency
            start_time = time.time()
            strategy = cfr_solver.solve(
                scenario['hole_cards'], 
                scenario['community_cards'], 
                scenario['pot_size'], 
                actions, 
                scenario['stage'],
                iterations=100  # Same as live bot
            )
            solve_time = time.time() - start_time
            strategies.append(strategy)
            times.append(solve_time)
        
        # Calculate averages
        avg_time = sum(times) / len(times)
        avg_strategy = {}
        for action in actions:
            avg_strategy[action] = sum(s.get(action, 0) for s in strategies) / len(strategies)
        
        print(f"   Avg Strategy: {format_strategy(avg_strategy)}")
        print(f"   Avg Time: {avg_time:.3f}s")
        
        # Quick quality assessment
        assessment = assess_strategy_quality(scenario, avg_strategy)
        print(f"   Assessment: {assessment}")

def format_strategy(strategy):
    """Format strategy for readable display."""
    formatted = {}
    for action, prob in strategy.items():
        if prob > 0.01:  # Only show actions with >1% probability
            formatted[action] = f"{prob:.3f}"
    return formatted

def assess_strategy_quality(scenario, strategy):
    """Simple assessment of whether the strategy makes sense."""
    name = scenario['name']
    
    # Get probabilities (default to 0 if action not in strategy)
    fold_prob = strategy.get(ACTION_FOLD, 0)
    check_prob = strategy.get(ACTION_CHECK, 0)
    call_prob = strategy.get(ACTION_CALL, 0)
    raise_prob = strategy.get(ACTION_RAISE, 0)
    
    if 'AA Preflop' in name:
        if raise_prob > 0.6:
            return "✅ GOOD - Raising with premium hand"
        elif call_prob > 0.3:
            return "⚠️  OK - Calling acceptable, but should raise more"
        else:
            return "❌ BAD - Not aggressive enough with AA"
    
    elif '72o Preflop' in name:
        if fold_prob > 0.7:
            return "✅ GOOD - Folding trash hand"
        elif check_prob > 0.5 and call_prob < 0.3:
            return "⚠️  OK - Checking acceptable in some spots"
        else:
            return "❌ BAD - Too loose with worst hand"
    
    elif 'Set on Dry Board' in name:
        if raise_prob > 0.5:
            return "✅ GOOD - Betting/raising with monster"
        elif check_prob > 0.3:
            return "⚠️  OK - Slowplaying can work sometimes"
        else:
            return "❌ BAD - Not extracting value from monster"
    
    elif 'Missed Draw' in name:
        if check_prob > 0.5 or fold_prob > 0.3:
            return "✅ GOOD - Playing conservatively with air"
        elif raise_prob > 0.3:
            return "❌ BAD - Bluffing too much with weak hand"
        else:
            return "⚠️  OK - Mixed strategy"
    
    elif 'Top Pair Good Kicker' in name:
        if raise_prob > 0.4 or (check_prob > 0.3 and call_prob > 0.3):
            return "✅ GOOD - Playing top pair aggressively"
        elif fold_prob > 0.3:
            return "❌ BAD - Folding top pair too often"
        else:
            return "⚠️  OK - Reasonable play"
    
    elif 'Weak Pair vs Scary Board' in name:
        if check_prob > 0.4 or fold_prob > 0.3:
            return "✅ GOOD - Playing cautiously on scary board"
        elif raise_prob > 0.4:
            return "❌ BAD - Too aggressive with weak hand"
        else:
            return "⚠️  OK - Mixed strategy"
    
    return "🤔 UNCLEAR - Needs human evaluation"

if __name__ == "__main__":
    test_cfr_decision_quality()
