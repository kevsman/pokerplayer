# opponent_model_utils.py

def update_opponent_model(opponent_models, player_name, action, amount, game_stage, pot_size, num_active_opponents_in_hand,
                          action_call_const, action_raise_const):
    if player_name not in opponent_models:
        opponent_models[player_name] = {
            'vpip_opportunities': 0, 'vpip_count': 0,        
            'pfr_opportunities': 0, 'pfr_count': 0,          
            'aggression_actions': 0, 'passive_actions': 0,    
            'fold_to_cbet_opportunities': 0, 'fold_to_cbet_count': 0,
            'cbet_opportunities': 0, 'cbet_count': 0, 
            'hands_observed': 0, 'action_history': [] 
        }
    
    model = opponent_models[player_name]
    model['action_history'].append((game_stage, action, amount, pot_size))

    if game_stage == 'Preflop':
        model['vpip_opportunities'] += 1 
        if action == action_call_const or action == action_raise_const:
            model['vpip_count'] += 1
            model['pfr_opportunities'] +=1 
            if action == action_raise_const:
                model['pfr_count'] += 1
    elif game_stage in ['Flop', 'Turn', 'River']:
        if action == action_raise_const: 
            model['aggression_actions'] += 1
        elif action == action_call_const:
            model['passive_actions'] += 1

def get_opponent_tendencies(opponent_models, player_name):
    model = opponent_models.get(player_name)
    if not model or model['vpip_opportunities'] < 10: 
        return {
            'vpip_rate': 0.25, 'pfr_rate': 0.15, 'agg_factor': 1.5, 
            'fold_to_cbet_rate': 0.5, 'cbet_rate': 0.6 
        } 
    
    vpip_rate = model['vpip_count'] / model['vpip_opportunities'] if model['vpip_opportunities'] > 0 else 0
    pfr_rate = model['pfr_count'] / model['pfr_opportunities'] if model['pfr_opportunities'] > 0 else 0
    
    agg_factor = (model['aggression_actions'] / model['passive_actions']) if model['passive_actions'] > 0 else (model['aggression_actions'] if model['aggression_actions'] > 0 else 1.5)
    
    cbet_rate = model['cbet_count'] / model['cbet_opportunities'] if model['cbet_opportunities'] > 0 else 0.6
    fold_to_cbet_rate = model['fold_to_cbet_count'] / model['fold_to_cbet_opportunities'] if model['fold_to_cbet_opportunities'] > 0 else 0.5

    return {
        'vpip_rate': round(vpip_rate, 2), 'pfr_rate': round(pfr_rate, 2), 'agg_factor': round(agg_factor, 2),
        'fold_to_cbet_rate': round(fold_to_cbet_rate, 2), 'cbet_rate': round(cbet_rate, 2)
    }
