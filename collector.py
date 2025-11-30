import datetime
import time
import requests
import database

#info about the athlete is stored in the database, so no need to store it here

global activities_cache #idk how this is workin atm
global last_fetch_date #last fetch date for activities

def refresh_access_token(client_id, client_secret, refresh_token):
    """Refresh Strava access token. Returns new access token."""
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    print(f"DEBUG: Refreshing access token for client_id: {client_id}")
    response = requests.post(token_url, data=payload)
    
    if response.status_code != 200:
        print(f"DEBUG: Token refresh failed with status {response.status_code}")
        print(f"DEBUG: Response: {response.text}")
        response.raise_for_status()
    
    tokens = response.json()
    access_token = tokens.get('access_token')
    if not access_token:
        print(f"DEBUG: Token response missing access_token. Full response: {tokens}")
        raise ValueError("Token refresh response missing access_token")
    
    print(f"DEBUG: Successfully refreshed access token (length: {len(access_token)})")
    return access_token

def get_current_user_information(username):
    #username is the session username
    client_id = database.get_client_id_from_username(username)
    client_secret = database.get_client_secret_by_username(username)
    refresh_token = database.get_refresh_token_by_username(username)

    access_token = refresh_access_token(client_id, client_secret, refresh_token)

    athlete_url = "https://www.strava.com/api/v3/athlete"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(athlete_url, headers=headers)
    response.raise_for_status()
    athlete_info = response.json()

    return athlete_info

def update_athlete_info_in_db(username):
    athlete_info = get_current_user_information(username)
    database.update_athlete_with_collector_info(username, athlete_info['firstname'], athlete_info['lastname'], athlete_info['sex'])


def fetch_activities(username):
    """Fetches activities from Strava API and stores them in cache. Returns activities or raises exception."""
    
    global activities_cache
    global last_fetch_date

    print(f"DEBUG: fetch_activities called for username: {username}")
    client_id = database.get_client_id_from_username(username)
    client_secret = database.get_client_secret_by_username(username)
    refresh_token = database.get_refresh_token_by_username(username)
    
    print(f"DEBUG: Retrieved credentials - client_id: {client_id}, has_secret: {bool(client_secret)}, has_refresh: {bool(refresh_token)}")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError('Missing Strava credentials in database')
    
    # Refresh access token
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    
    # Get activities from Strava API
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # params = {
    #     "per_page": 10
    # }
    
    print(f"DEBUG: Making API call to fetch activities from Strava")
    print(f"DEBUG: Using access token (first 20 chars): {access_token[:20] if access_token else 'None'}...")
    response = requests.get(activities_url, headers=headers)
    
    # Log response details for debugging
    print(f"DEBUG: Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"DEBUG: Response text: {response.text[:500]}")
        try:
            error_json = response.json()
            print(f"DEBUG: Error JSON: {error_json}")
            # Check for scope/permission errors
            if 'errors' in error_json:
                for error in error_json.get('errors', []):
                    if 'activity:read' in str(error.get('field', '')):
                        print(f"ERROR: Access token is missing 'activity:read' scope!")
                        print(f"ERROR: You need to re-authenticate with Strava to get a token with the correct scopes.")
                        print(f"ERROR: Use the OAuth flow at /connect/strava or get a new refresh token with 'activity:read_all' scope.")
        except:
            pass
        print(f"DEBUG: Response headers: {dict(response.headers)}")
        print(f"DEBUG: Request URL: {activities_url}")
        print(f"DEBUG: Request headers: {headers}")
    
    response.raise_for_status()
    activities = response.json()
    print(f"DEBUG: Successfully fetched {len(activities)} activities from Strava")
    
    # Store activities in cache
    activities_cache = activities
    last_fetch_date = datetime.datetime.now()
    
    return activities

def add_initial_activities_to_db(username):
    print(f"DEBUG: add_initial_activities_to_db called for username: {username}")
    activities = fetch_activities(username)
    print(f"DEBUG: Got {len(activities)} activities from fetch_activities")
    user_id = database.get_user_id_from_username(username)
    print(f"DEBUG: User ID: {user_id}")
    
    activities_added = 0
    activities_skipped = 0
    
    for activity in activities:
        start_date = activity['start_date']
        date_string = start_date[:10]

        distance_meters = activity['distance']
        distance_miles = distance_meters * 0.000621371

        if not database.activity_exists(user_id, date_string, distance_miles, activity['name']):
            database.create_activity(user_id, date_string, distance_miles, activity['name'])
            activities_added += 1
        else:
            activities_skipped += 1
    
    print(f"DEBUG: Added {activities_added} new activities, skipped {activities_skipped} existing activities")

def add_new_activities_to_db(username, date):
    activities = fetch_activities_after_date(username, date)
    user_id = database.get_user_id_from_username(username)
    for activity in activities:
        start_date = activity['start_date']
        date_string = start_date[:10]

        distance_meters = activity['distance']
        distance_miles = distance_meters * 0.000621371

        if not database.activity_exists(user_id, date_string, distance_miles, activity['name']):
            database.create_activity(user_id, date_string, distance_miles, activity['name'])


def fetch_activities_after_date(username, date):
    """Fetches activities from Strava API and stores them in cache. Returns activities or raises exception."""
    global activities_cache
    global last_fetch_date
    
    date_utc = datetime.datetime.strptime(date, "%Y-%m-%d")
    date_timestamp = int(time.mktime(date_utc.timetuple()))

    client_id = database.get_client_id_from_username(username)
    client_secret = database.get_client_secret_by_username(username)
    refresh_token = database.get_refresh_token_by_username(username)
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError('Missing Strava credentials in database')
    
    # Refresh access token
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    
    # Get activities from Strava API
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "after": date_timestamp
    }
    
    response = requests.get(activities_url, headers=headers, params=params)
    response.raise_for_status()
    activities = response.json()
    
    # Store activities in cache
    activities_cache = activities
    last_fetch_date = datetime.datetime.now()
    
    return activities