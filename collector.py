import os
from dotenv import load_dotenv
import datetime
import time
import requests
import database

#info about the athlete is stored in the database, so no need to store it here

load_dotenv()

def exchange_code_for_tokens(code):
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post("https://www.strava.com/oauth/token", data=payload)

    if response.status_code != 200:
        print(f"Error exchanging code: {response.text}")
        response.raise_for_status()

    return response.json()

def authorize_and_save_user(code, user_id):
    data = exchange_code_for_tokens(code)

    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    expires_at = data.get('expires_at')

    athlete_info = data.get('athlete', {})

    strava_id = athlete_info.get('id')
    first_name = athlete_info.get('firstname')
    last_name = athlete_info.get('lastname')
    gender = athlete_info.get('sex')

    database.save_user_tokens_and_info(
        user_id,
        access_token,
        refresh_token,
        expires_at,
        strava_id,
        first_name,
        last_name,
        gender
    )

def get_valid_access_token(user_id):
    tokens = database.get_user_tokens(user_id)

    if not tokens:
        print(f"No tokens found for User: {user_id}")
        return None
    
    access_token = tokens['strava_access_token']
    refresh_token = tokens['strava_refresh_token']
    token_expiration = tokens['token_expiration']
    
    if token_expiration is None or time.time() > (token_expiration - 300):
        print(f"DEBUG: Refreshing token for User {user_id}")
        return refresh_access_token(user_id, refresh_token)

    return access_token


def refresh_access_token(user_id, refresh_token):
    client_id = os.getenv('STRAVA_CLIENT_ID')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')
    """Refresh Strava access token. Returns new access token."""
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    data = response.json()

    database.update_user_tokens(
        user_id,
        data['access_token'],
        data['refresh_token'],
        data['expires_at']
    )

    return data['access_token']

def fetch_and_save_user_data(user_id):
    seconds_in_30_days = 2592000

    try:
        token = get_valid_access_token(user_id)

        start_date = int(time.time()) - seconds_in_30_days

        url = "https://www.strava.com/api/v3/athlete/activities"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"after": start_date, "per_page": 50}

        response = requests.get(url,headers=headers, params=params)
        response.raise_for_status()
        activities = response.json()

        count = 0
        for activity in activities:
            miles = round(activity['distance'] * 0.000621371, 2)
            date_str = activity['start_date_local'].split('T')[0]
            title = activity['name']

            database.create_activity(
                user_id=user_id,
                date=date_str,
                distance=miles,
                title=title

            )
            count += 1

        print(f"Imported {count} activities for User: {user_id}")

    except Exception as e:
        print(f"Error for User {user_id}: {e}")