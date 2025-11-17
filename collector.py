# collector.py
import sqlite3
import datetime
import random
import requests
import os
from dotenv import load_dotenv
import datetime
import time

DB_NAME = "MileageTracker.db"

last_fetch_date = None
global activities_cache

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        #Resetting the tables each time collector is run to maintain known state
        cursor.execute("DROP TABLE IF EXISTS DailyMileage")
        cursor.execute("DROP TABLE IF EXISTS Athletes")
        
        # Athlete table
        cursor.execute("""
        CREATE TABLE Athletes (
            athlete_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            gender TEXT CHECK(gender IN ('M', 'F', 'O')) DEFAULT 'O',
            mileage_goal REAL,
            long_run_goal REAL
        )
        """)

        # DailyMileage table
        cursor.execute("""
        CREATE TABLE DailyMileage (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            distance REAL,
            activity_title VARCHAR(100),
            athlete_id INTEGER,
            FOREIGN KEY (athlete_id) REFERENCES Athletes(athlete_id)
        )
        """)

        conn.commit()


def add_example_data():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            athletes = [
                (1, "John", "Smith", "M", 30.0, 8.0)
            ]

            athlete_ids = []
            for athlete in athletes:
                cursor.execute("INSERT INTO Athletes (client_id, first_name, last_name, gender, mileage_goal, long_run_goal) VALUES (?,?,?,?,?)", athlete)

                athlete_ids.append(cursor.lastrowid)

            base_time = datetime.datetime.now()

            for athlete_id in athlete_ids:
                for i in range(14):
                    day = base_time - datetime.timedelta(days = i)
                    dist = round(random.uniform(3.0, 10.0), 2)
                    title = "None"

                    cursor.execute(
                        "INSERT INTO DailyMileage (date, distance, activity_title, athlete_id) VALUES (?, ?, ?, ?)",
                        (day.date(), dist, title, athlete_id)
                    )

            conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

def get_latest_fetch_date():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM DailyMileage")
        result = cursor.fetchone()[0]
        #last_fetch_date = result
        return result

def fetch_new_activities():
    last_fetch_date = get_latest_fetch_date()

    if last_fetch_date is None:
        # If no activities in database, fetch from 1 year ago to get all recent activities
        one_month_ago = datetime.datetime.now() - datetime.timedelta(days=28)
        # Convert to Unix timestamp (Strava API expects Unix timestamp)
        default_date = int(one_month_ago.timestamp())
        #global activities_cache
        activities = fetch_activities_after_date(default_date)
        activities_cache = activities
        return activities
    else:
        # Convert date string to Unix timestamp if needed
        # If last_fetch_date is already a timestamp, use it directly
        # Otherwise convert from date string
        if isinstance(last_fetch_date, str):
            date_obj = datetime.datetime.strptime(last_fetch_date, "%Y-%m-%d")
            date_timestamp = int(date_obj.timestamp())
        else:
            date_timestamp = last_fetch_date
        
        #global activities_cache
        activities = fetch_activities_after_date(date_timestamp)
        activities_cache = activities
        return activities
    

def fetch_activities_after_date(date):
    """Fetches activities from Strava API and stores them in cache. Returns activities or raises exception."""
    global activities_cache
    
    # Get credentials from .env file
    client_id = os.getenv('STRAVA_CLIENT_ID')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')
    refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError('Missing Strava credentials in .env file')
    
    # Refresh access token
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    
    # Get activities from Strava API
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "after": date
    }
    
    response = requests.get(activities_url, headers=headers, params=params)
    response.raise_for_status()
    activities = response.json()
    
    # Store activities in cache
    #activities_cache = activities
    
    return activities

# Function to get a new access token using the refresh token
def refresh_access_token(client_id, client_secret, refresh_token):
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    tokens = response.json()
    return tokens['access_token']

if __name__ == "__main__":
    init_db()
    add_example_data()
    print("---")
    print("Collector finished. You can now run app.py")

def transform_strava_activity(strava_activity):
    """Transform a Strava API activity response to database format."""
    # Extract date from start_date_local (format: "2024-01-15T10:30:00Z" or "2024-01-15T10:30:00")
    start_date = strava_activity.get('start_date_local') or strava_activity.get('start_date', '')
    # Parse the ISO format date and extract just the date part
    if start_date:
        try:
            # Handle different timezone formats
            if start_date.endswith('Z'):
                date_obj = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                # Try parsing without timezone first
                try:
                    date_obj = datetime.datetime.fromisoformat(start_date)
                except ValueError:
                    # Fallback: try parsing just the date part
                    date_obj = datetime.datetime.strptime(start_date.split('T')[0], '%Y-%m-%d')
            date_str = date_obj.date().isoformat()
        except (ValueError, AttributeError):
            date_str = datetime.datetime.now().date().isoformat()
    else:
        date_str = datetime.datetime.now().date().isoformat()
    
    # Convert distance from meters to miles (1 meter = 0.000621371 miles)
    distance_meters = strava_activity.get('distance', 0)
    distance_miles = distance_meters * 0.000621371
    
    # Get activity name, default to "None" if not provided
    activity_title = strava_activity.get('name', 'None')
    
    return {
        'date': date_str,
        'distance': round(distance_miles, 2),
        'activity_title': activity_title
    }

def add_new_activities_to_db(activities, athlete_id):
    if activities is None or len(activities) == 0:
        return []
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for strava_activity in activities:
            # Transform Strava activity to database format
            activity = transform_strava_activity(strava_activity)
            cursor.execute("INSERT INTO DailyMileage (date, distance, activity_title, athlete_id) VALUES (?, ?, ?, ?)", 
                         (activity['date'], activity['distance'], activity['activity_title'], athlete_id))
        conn.commit()
    return activities

def add_strava_athlete_to_db():
    #client_id = os.getenv('STRAVA_CLIENT_ID')
    #have to make sure you do not add the athlete to the database if they are already in the database (by client_id -- which is provided in the json response from getting athlete info)
    athlete_info = get_strava_athlete_info()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Athletes (client_id, first_name, last_name, gender, mileage_goal, long_run_goal) VALUES (?, ?, ?, ?, ?, ?)", (athlete_info['id'], athlete_info['firstname'], athlete_info['lastname'], athlete_info['sex'], 0, 0))
        conn.commit()
    #initially makes mileage goal & lr 0 cuz it will be edited on the html page

def get_strava_athlete_info():
    athlete_url = "https://www.strava.com/api/v3/athlete"
    client_id = os.getenv('STRAVA_CLIENT_ID')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')
    refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError('Missing Strava credentials in .env file')

    access_token = refresh_access_token(client_id, client_secret, refresh_token)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(athlete_url, headers=headers)
    response.raise_for_status()
    athlete = response.json()
    return athlete
    #info we need from response is id, firstname, lastname, sex (mileage & lr goal will initially be 0)

def change_mileage_goal(new_goal, athlete_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Athletes SET mileage_goal = ? WHERE id = ?", (new_goal, athlete_id))
        conn.commit()
    return new_goal

def change_long_run_goal(new_goal, athlete_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Athletes SET long_run_goal = ? WHERE id = ?", (new_goal, athlete_id))
        conn.commit()
    return new_goal

def fetch_activities():
    """Fetches activities from Strava API and stores them in cache. Returns activities or raises exception."""
    global activities_cache
    
    # Get credentials from .env file
    client_id = os.getenv('STRAVA_CLIENT_ID')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')
    refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError('Missing Strava credentials in .env file')
    
    # Refresh access token
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    
    # Get activities from Strava API
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "per_page": 10
    }
    
    response = requests.get(activities_url, headers=headers, params=params)
    response.raise_for_status()
    activities = response.json()
    
    # Store activities in cache
    activities_cache = activities
    
    return activities