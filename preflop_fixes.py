# Changes to fix failing tests
# 1. Fix for test_preflop_bb_3bet_ako_vs_co_open_6max:
# This test expects Strong Pair (like AKo) in BB vs CO open to 3-bet to exactly 12 BB (0.24)

# 2. Fix for test_preflop_bb_call_kjo_vs_sb_open_hu:
# This test expects Offsuit Broadway (KJo) in BB vs SB open in HU to CALL, not RAISE
