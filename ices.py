import requests
import csv
from datetime import datetime

def get_current_nfl_week():
    url = "https://api.sleeper.app/v1/state/nfl"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('week', 1)
    else:
        print("Failed to fetch current NFL week. Defaulting to week 1.")
        return 1

def get_league_data(league_id):
    users_url = f"https://api.sleeper.app/v1/league/{league_id}/users"
    users_response = requests.get(users_url)

    if users_response.status_code == 200:
        users_data = users_response.json()
        return users_data
    else:
        print(f"Failed to fetch league data. Status: {users_response.status_code}")
        return None

def get_player_stats(season, week):
    url = f"https://api.sleeper.app/v1/stats/nfl/{season}/{week}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch stats for week {week}. Status code: {response.status_code}")
        return {}

def get_player_name(player_id):
    url = f"https://api.sleeper.app/v1/players/nfl/{player_id}"
    response = requests.get(url)
    if response.status_code == 200:
        player = response.json()
        return f"{player.get('first_name', '')} {player.get('last_name', '')}"
    return player_id

def get_weekly_matchups(league_id, week):
    url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch matchups for week {week}. Status code: {response.status_code}")
        return None

# Replace with your league ID
league_id = "1117180538298658816"
season = "2024"
current_week = 6
get_current_nfl_week()

users_data = get_league_data(league_id)

if users_data is None:
    print("Failed to fetch league data.")
    exit()

# Create a dictionary to map user_id to team name
team_names = {user['user_id']: user.get('metadata', {}).get('team_name', user['display_name']) for user in users_data}

# Initialize dictionaries to store weekly and season totals
weekly_zero_players = {team: {} for team in team_names.values()}
season_zero_count = {team: 0 for team in team_names.values()}

# Process each week up to the current week
for week in range(1, current_week + 1):
    print(f"Processing week {week}")
    weekly_stats = get_player_stats(season, week)
    weekly_matchups = get_weekly_matchups(league_id, week)
    
    if not weekly_stats or not weekly_matchups:
        print(f"Skipping week {week} due to missing data")
        continue
    
    for matchup in weekly_matchups:
        team_name = team_names.get(str(matchup['roster_id']), 'Unknown')
        starters = matchup['starters']
        
        for player_id in starters:
            player_stats = weekly_stats.get(player_id, {})
            points = player_stats.get('pts_ppr', 0) or 0  # Use 0 if None
            
            if points <= 0:
                if week == current_week:
                    player_name = get_player_name(player_id)
                    weekly_zero_players[team_name][player_name] = points
                season_zero_count[team_name] += 1
                print(f"Week {week}: {team_name} - {get_player_name(player_id)}: {points}")  # Debug print

# Generate a filename with the current date and week
current_date = datetime.now().strftime("%Y%m%d")
filename = f"zero_points_summary_{current_date}_week{current_week}.md"

# Write the data to a markdown file
with open(filename, 'w') as mdfile:
    mdfile.write(f"# Zero Points Summary for Week {current_week} (Starters Only)\n\n")
    mdfile.write("| Team | Current Week Zero or Less | Season Total Zero or Less |\n")
    mdfile.write("|------|---------------------------|----------------------------|\n")
    for team in team_names.values():
        current_week_players = "<br>".join([f"{name}: {points}" for name, points in weekly_zero_players[team].items()])
        mdfile.write(f"| {team} | {current_week_players} | {season_zero_count[team]} |\n")

print(f"Summary for Week {current_week} has been saved to {filename}")
