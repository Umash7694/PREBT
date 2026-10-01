import json
import os

HISTORY_FILE = 'history.json'

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading history.json: {e}")
        return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving history.json: {e}")

def record_daily_predictions(date_str, predictions):
    """
    Saves the exact matches analyzed by app.py into history.
    """
    history = load_history()
    
    # Store exact 20 matches sent from app.py
    history[date_str] = {
        "matches": predictions,
        "summary": {
            "total": len(predictions),
            "won": 0,
            "lost": 0,
            "pending": len(predictions)
        }
    }
    save_history(history)

def update_daily_results(target_date, live_matches_api):
    """
    Tracks finished games from API-Sports in real-time and determines WON / LOST.
    """
    history = load_history()
    if target_date not in history:
        return

    # Map API fixtures by fixture ID
    api_map = {str(item.get('fixture', {}).get('id')): item for item in live_matches_api}

    updated = False
    for match in history[target_date].get('matches', []):
        match_id = str(match.get('match_id'))
        
        if match_id in api_map:
            fixture_data = api_map[match_id]
            status_short = fixture_data.get('fixture', {}).get('status', {}).get('short', '')
            
            # Finished match statuses in API-Sports
            if status_short in ['FT', 'AET', 'PEN']:
                home_goals = fixture_data.get('goals', {}).get('home')
                away_goals = fixture_data.get('goals', {}).get('away')
                
                if home_goals is not None and away_goals is not None:
                    total_goals = home_goals + away_goals
                    match['score'] = f"{home_goals} - {away_goals}"
                    
                    pred = match.get('predicted_outcome', '')
                    home_team = match.get('home_team', '')
                    away_team = match.get('away_team', '')
                    
                    # Live outcome evaluation engine
                    if 'Over 2.5' in pred:
                        match['result'] = 'WON' if total_goals > 2.5 else 'LOST'
                    elif 'Under 2.5' in pred:
                        match['result'] = 'WON' if total_goals < 2.5 else 'LOST'
                    elif 'Over 0.5 HT' in pred:
                        ht_home = fixture_data.get('score', {}).get('halftime', {}).get('home', 0) or 0
                        ht_away = fixture_data.get('score', {}).get('halftime', {}).get('away', 0) or 0
                        match['result'] = 'WON' if (ht_home + ht_away) > 0.5 else 'LOST'
                    elif 'BTTS Yes' in pred:
                        match['result'] = 'WON' if (home_goals > 0 and away_goals > 0) else 'LOST'
                    elif 'BTTS No' in pred:
                        match['result'] = 'WON' if (home_goals == 0 or away_goals == 0) else 'LOST'
                    elif f"{home_team} Win" in pred:
                        match['result'] = 'WON' if home_goals > away_goals else 'LOST'
                    elif f"{away_team} Win" in pred:
                        match['result'] = 'WON' if away_goals > home_goals else 'LOST'
                    elif f"{home_team} DNB" in pred:
                        if home_goals > away_goals:
                            match['result'] = 'WON'
                        elif home_goals == away_goals:
                            match['result'] = 'PENDING'  # Refund / Push
                        else:
                            match['result'] = 'LOST'
                    else:
                        match['result'] = 'PENDING'
                    
                    updated = True

    if updated:
        matches = history[target_date]['matches']
        history[target_date]['summary'] = {
            "total": len(matches),
            "won": sum(1 for m in matches if m.get('result') == 'WON'),
            "lost": sum(1 for m in matches if m.get('result') == 'LOST'),
            "pending": sum(1 for m in matches if m.get('result') not in ['WON', 'LOST'])
        }
        save_history(history)