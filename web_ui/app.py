import streamlit as st
import json 
from datetime import datetime
import os
import requests
import pandas as pd
from nba_api.stats.static import teams
from nba_api.stats.static import players
from nba_api.stats.endpoints import teamyearbyyearstats, playercareerstats


def main():
    if st.session_state.get('logged_in'):
        navigation_bar()
        page_router()
    else:
        login_page()


def page_router():
    if st.session_state['current_page'] == 'favorites':
        favorites_page()
    elif st.session_state['current_page'] == 'profile':
        expanded_profile_page()
    # elif st.session_state['current_page'] == 'social': 
    #     social_page()

def navigation_bar():
    pages = {
        "Modify Profile": "favorites",
        "Profile Stats": "profile",
        # "Social": "social",
    }
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a Page", list(pages.keys()))
    st.session_state['current_page'] = pages[page]


def login_page():
    st.title("Login Page")
    username = st.text_input("Username", key='login_username')
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        timestamp = datetime.now().strftime("%Y%m%d%H")
        response = requests.post('http://127.0.0.1:5000/login', json=
        {
            "username": username,
            "password": password,
            "date": timestamp
        })
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)  # Check what the actual response is
        if response.status_code == 200:
            st.session_state['logged_in'] = True
            st.session_state['current_page'] = 'favorites'
            st.session_state['username'] = username
            st.session_state['login_timestamp'] = timestamp
            st.success("Logged in successfully!")
            favorites_page()  # Direct call after success
        else:
            st.error("Failed to log in: " + response.json().get('error', 'Unknown error'))
        st.rerun()

def get_nba_teams():
    nba_teams = teams.get_teams()
    team_names = [team['full_name'] for team in nba_teams]
    return team_names

def get_nba_players():
    nba_players = players.get_active_players()
    player_names = [player['full_name'] for player in nba_players]
    return player_names


def favorites_page():
    st.title("Modify your preferences")
    if 'username' not in st.session_state or not st.session_state['username']:
        st.error("User not identified.")
        return
    display_preferences_selection()
    if st.button('Show My Preferences'):
        display_user_preferences(st.session_state['username'])

def display_preferences_selection():
    nba_teams = get_nba_teams()
    nba_players = get_nba_players()

    favorite_teams = st.multiselect("Select your favorite team", nba_teams)
    bandwagon_teams = st.multiselect("Select your bandwagon teams", nba_teams, default=None)
    rival = st.multiselect("Select your least favorite teams", nba_teams, default=None)
    favorite_players = st.multiselect("Select your favorite players", nba_players)

    preferences_data = {
        'favorite_teams': favorite_teams,
        'bandwagon_teams': bandwagon_teams,
        'rival': rival,
        'favorite_players': favorite_players
    }

    if st.button('Save My Preferences'):
        save_preferences(preferences_data)
    if st.button('Delete My Preferences'):
        delete_preferences()


def save_preferences(preferences):
    user_preferences = {
        "username": st.session_state['username'],
        "timestamp": st.session_state['login_timestamp'],
        "favorite_teams": preferences['favorite_teams'],
        "bandwagon_teams": preferences['bandwagon_teams'],
        "rival_teams": preferences['rival'],
        "favorite_players": preferences['favorite_players']
    }

    print("JSON being sent to the server:", user_preferences)
    api_url = 'http://127.0.0.1:5000/api/save_preferences'

    try:
        response = requests.post(api_url, json=user_preferences)
        if response.status_code == 200:
            st.success('Your preferences have been saved.')
        else:
            st.error(f"Failed to update preferences: {response.json().get('message', 'Unknown error')}")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the server: {str(e)}")


def delete_preferences():
    user_preferences = {
        "username": st.session_state.get('username'),
        "timestamp": st.session_state.get('login_timestamp')
    }
    if user_preferences["username"] and user_preferences["timestamp"]:
        api_url = 'http://127.0.0.1:5000/api/delete_preferences'
        try:
            response = requests.post(api_url, json=user_preferences)
            if response.status_code == 200:
                st.session_state['preferences'] = None
                st.success('Your preferences have been deleted.')
            else:
                st.error(f"Failed to delete preferences: {response.json().get('message', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the server: {str(e)}")
    else:
        st.error('No preferences found to delete.')

def display_user_preferences(username):
    if 'login_timestamp' in st.session_state:
        timestamp = st.session_state['login_timestamp']
        url = f'http://127.0.0.1:5000/api/preferences/{username}?timestamp={timestamp}'
        response = requests.get(url)
        
        if response.status_code == 200:
            preferences = response.json()
            print("Preferences fetched from the server:", preferences)
            st.subheader("Your Profile:")

            rows = []
            for pref_type, entities in preferences.items():
                for entity in entities:
                    if 'team' in pref_type:
                        # record = get_team_record(entity)
                        if pref_type == 'favorite_teams':
                            rows.append((entity, "Team", "Favorite"))
                        if pref_type == 'bandwagon_teams':
                            rows.append((entity, "Team", "Bandwagon"))
                    elif 'player' in pref_type:
                        # stats = get_player_stats(entity)
                        rows.append((entity, "Player", "Favorite Player"))  # Include pref_type and "N/A" for missing stats
                    else:
                        rows.append((entity, "Team", "Rivalry"))  # Include pref_type

            df = pd.DataFrame(rows, columns=[ "NBA Entity", "Type", "Preference Type"])
            df.reset_index(drop=True, inplace=True)
            st.dataframe(df)
        else:
            st.error(f"Failed to fetch preferences: {response.json().get('error', 'Unknown error')}")
    else:
        st.error("No login date found. Please log in again.")


def expanded_profile_page():
    # Access username directly from session state
    if 'username' in st.session_state and 'login_timestamp' in st.session_state:
        username = st.session_state['username']
        timestamp = st.session_state['login_timestamp']
        url = f'http://127.0.0.1:5000/api/preferences/{username}?timestamp={timestamp}'
        response = requests.get(url)

        if response.status_code == 200:
            preferences = response.json()
            print("Preferences fetched from the server:", preferences)
            st.subheader("Detailed Profile Page:")

            liked_team_rows = []
            rival_team_rows = []
            player_rows = []

            for pref_type, entities in preferences.items():
                for entity in entities:
                    if 'team' in pref_type:
                        record = get_team_record(entity)
                        liked_team_rows.append((entity, pref_type, record))

                    elif 'rival' in pref_type:
                        record = get_team_record(entity)
                        rival_team_rows.append((entity, pref_type, record))

                    elif 'player' in pref_type:
                        # Placeholder for potential actual data fetching function
                        stats = get_player_stats(entity)
                        if stats:
                            player_rows.append((entity, pref_type) + stats)

            # Create DataFrames for each category
            liked_team_df = pd.DataFrame(liked_team_rows, columns=["Team Name","Preference Type", "Record"])
            player_df = pd.DataFrame(player_rows, columns=[ "Player Name", "Preference Type", "Age", "Games Played", "3PT FG%", "FG%", "FT%", "Points per Game", "Rebounds per Game", "Assists per Game"])
            rival_team_df = pd.DataFrame(rival_team_rows, columns=["Team Name","Preference Type", "Record"])
            # Display DataFrames in separate sections
            if not liked_team_df.empty:
                st.subheader("Preferred Teams")
                st.dataframe(liked_team_df)
            else:
                st.write("You do not have any liked or bandwagon teams")

            if not rival_team_df.empty:
                st.subheader("Rival Teams")
                st.dataframe(rival_team_df)
            else:
                st.write("You do not have any rivalry teams")

            if not player_df.empty:
                st.subheader("Preferred Players")
                st.dataframe(player_df)
            else:
                st.write("You do not have any favorite players")

        else:
            st.error(f"Failed to fetch preferences: {response.json().get('error', 'Unknown error')}")
    else:
        st.error("Login or username data missing. Please log in again.")




def get_team_record(team_name):
    nba_teams = teams.get_teams()
    team_dict = [team for team in nba_teams if team['full_name'] == team_name]
    if team_dict:
        team_id = team_dict[0]['id']
        team_stats = teamyearbyyearstats.TeamYearByYearStats(team_id=team_id)
        recent_season = team_stats.get_data_frames()[0].iloc[-1]  # Get the most recent season record
        return f"{recent_season['WINS']}-{recent_season['LOSSES']}"
    return "N/A"


def get_player_stats(player_name):
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playercareerstats
    
    nba_players = players.get_active_players()
    player_dict = [player for player in nba_players if player['full_name'] == player_name]
    if player_dict:
        player_id = player_dict[0]['id']
        player_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        stats_df = player_stats.get_data_frames()[0]
        
        # Extracting required statistics
        player_age = stats_df.iloc[0]['PLAYER_AGE']
        GP = stats_df.iloc[0]['GP']
        FG3_PCT = stats_df.iloc[0]['FG3_PCT']
        FG_PCT = stats_df.iloc[0]['FG_PCT']
        FT_PCT = stats_df.iloc[0]['FT_PCT']
        PTS = stats_df.iloc[0]['PTS']
        REB = stats_df.iloc[0]['REB']
        AST = stats_df.iloc[0]['AST']
        
        # Calculating additional statistics
        Pts_per_game = PTS / GP
        REB_per_game = REB / GP
        Ast_per_game = AST / GP
        
        # Returning the selected and calculated statistics as a tuple
        return (
            player_age, GP, FG3_PCT, FG_PCT, FT_PCT, 
            Pts_per_game, REB_per_game, Ast_per_game
        )
    else:
        return None

# def social_page():
#     st.title("Social Connections")
#     st.subheader("See how many users share your specific NBA preferences")
    
#     # Check user login status
#     if 'username' not in st.session_state or not st.session_state['username']:
#         st.error("User not identified. Please log in.")
#         return
    
#     username = st.session_state['username']
    
#     # Check for a valid timestamp
#     if 'login_timestamp' in st.session_state:
#         timestamp = st.session_state['login_timestamp']
#         url = f'http://127.0.0.1:5000/api/shared_preferences/{username}?timestamp={timestamp}'
        
#         try:
#             # Make the GET request to the server
#             response = requests.get(url)
#             if response.status_code == 200:
#                 # Parse and display data if successful
#                 data = response.json()
#                 if data:
#                     st.subheader("Shared Preferences")
#                     for pref, count in data.items():
#                         st.write(f"**{pref.replace('_', ' ')}**: {count} users")
#                 else:
#                     st.write("No data available on shared preferences.")
#             else:
#                 # Handle errors in fetching data
#                 st.error(f"Failed to fetch shared preferences: {response.json().get('error', 'Unknown error')}")
#         except requests.exceptions.RequestException as e:
#             st.error(f"Connection error: {str(e)}")
#     else:
#         st.error("No login timestamp found. Please log in again.")



if __name__ == "__main__":
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 'login'
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    main()