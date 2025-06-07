print("Starting test...")

try:
    print("Importing modules...")
    from postflop_decision_logic import make_postflop_decision
    print("✓ postflop_decision_logic imported")
    
    from decision_engine import DecisionEngine
    print("✓ decision_engine imported")
    
    from opponent_tracking import OpponentTracker
    print("✓ opponent_tracking imported")
    
    print("✓ All imports successful")
    
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()

print("Test completed.")
