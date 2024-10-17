import requests
import json
from datetime import datetime
import os


def get_weekly_results(week, league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch matchup data. Status: {response.status_code}")
        return None


def get_team_names(league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/users"
    response = requests.get(url)
    if response.status_code == 200:
        users_data = response.json()
        # Fetch rosters to get the mapping between user_id and roster_id
        rosters_url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
        rosters_response = requests.get(rosters_url)
        if rosters_response.status_code == 200:
            rosters_data = rosters_response.json()
            user_to_roster = {roster['owner_id']: roster['roster_id'] for roster in rosters_data}
            return {user_to_roster[user['user_id']]: user['display_name'] for user in users_data if user['user_id'] in user_to_roster}
        else:
            print(f"Failed to fetch roster data. Status: {rosters_response.status_code}")
            return None
    else:
        print(f"Failed to fetch user data. Status: {response.status_code}")
        return None
    

def filter_low_scoring_starters(data):
    filtered_data = []
    for team in data:
        low_scoring_starters = []
        low_scoring_points = []
        for starter, points in zip(team['starters'], team['starters_points']):
            if points <= 0:
                low_scoring_starters.append(starter)
                low_scoring_points.append(points)
        
        if low_scoring_starters:
            filtered_team = {
                'team_name': team['team_name'],
                'low_scoring_starters': low_scoring_starters,
                'low_scoring_points': low_scoring_points
            }
            filtered_data.append(filtered_team)
    
    return filtered_data
    

def get_current_week():
    url = "https://api.sleeper.app/v1/state/nfl"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['week']
    else:
        print(f"Failed to fetch current week. Status: {response.status_code}")
        return None

def has_non_zero_points(weekly_results):
    return any(any(points != 0 for points in team['starters_points']) for team in weekly_results)

def get_player_names(player_ids):
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    if response.status_code == 200:
        all_players = response.json()
        return {pid: all_players[pid].get('full_name', all_players[pid].get('first_name', '') + ' ' + all_players[pid].get('last_name', '')) for pid in player_ids if pid in all_players}
    else:
        print(f"Failed to fetch player data. Status: {response.status_code}")
        return {}

def translate_player_ids(low_scoring_data):
    if not isinstance(low_scoring_data, list):
        if isinstance(low_scoring_data, dict) and 'low_scoring_starters' in low_scoring_data:
            low_scoring_data = low_scoring_data['low_scoring_starters']
        else:
            print(f"Warning: Unexpected low_scoring_data format. Type: {type(low_scoring_data)}")
            return low_scoring_data

    all_player_ids = set()
    for team in low_scoring_data:
        if not isinstance(team, dict):
            print(f"Warning: team is not a dictionary. Type: {type(team)}")
            continue
        if 'low_scoring_starters' not in team:
            print(f"Warning: 'low_scoring_starters' not found in team data: {team}")
            continue
        all_player_ids.update(team['low_scoring_starters'])
    
    player_names = get_player_names(all_player_ids)
    
    for team in low_scoring_data:
        if isinstance(team, dict) and 'low_scoring_starters' in team:
            team['low_scoring_starters'] = [player_names.get(pid, pid) for pid in team['low_scoring_starters']]
    
    return low_scoring_data

def get_lowest_scoring_team(weekly_results, team_names):
    if not weekly_results:
        return None
    
    lowest_team = min(weekly_results, key=lambda x: sum(x['starters_points']))
    roster_id = lowest_team['roster_id']
    return {
        'team_name': team_names.get(roster_id, f"Unknown Team {roster_id}"),
        'total_points': sum(lowest_team['starters_points'])
    }

def find_lowest_scoring_team(week):
    weekly_results = get_weekly_results(week, league_id)
    team_names = get_team_names(league_id)
    
    if not weekly_results or not team_names:
        return None
    
    lowest_team = min(weekly_results, key=lambda x: x['points'])
    roster_id = lowest_team['roster_id']
    
    return {
        'team_name': team_names.get(roster_id, f"Unknown Team {roster_id}"),
        'points': lowest_team['points']
    }

# Make sure to define league_id at the top of your script if it's not already there
league_id = "1117180538298658816"

current_week = get_current_week()

if current_week:
    weeks = range(1, current_week + 1)
    team_names = get_team_names(league_id)

    results = []
    for week in weeks:
        filename = f'low_scoring_starters_week_{week}.json'
        
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                low_scoring_data = json.load(f)
        else:
            low_scoring_data = []
        
        # Process the week's data regardless of whether low_scoring_data is empty
        low_scoring_data = translate_player_ids(low_scoring_data)
        
        # Find the lowest scoring team for this week
        lowest_scoring_team = find_lowest_scoring_team(week)
        
        if lowest_scoring_team:
            # Add the lowest scoring team to the results
            results.append({
                'week': week,
                'team': lowest_scoring_team['team_name'],
                'score': lowest_scoring_team['points'],
                'low_scorers': low_scoring_data
            })
        else:
            print(f"No team data available for week {week}")

    # Write results to a JSON file
    current_date = datetime.now().strftime("%Y%m%d")
    output_filename = f'weekly_results_{current_date}.json'
    with open(output_filename, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results have been written to {output_filename}")

    # Optional: You can keep or remove this part that prints to console
    for result in results:
        print(f"Lowest scoring team for week {result['week']}: {result['team']} with {result['score']} points")
        print(f"Low scoring starters: {result['low_scorers']}")
else:
    print("Failed to determine the current week.")
