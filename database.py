import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "MileageTracker.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        #Resetting the tables each time collector is run to maintain known state
        #these 3 lines will be commented out when we are done testing
        cursor.execute("DROP TABLE IF EXISTS Users")
        cursor.execute("DROP TABLE IF EXISTS DailyMileage")
        cursor.execute("DROP TABLE IF EXISTS Athletes")
        
        # User table
        cursor.execute("""
        CREATE TABLE Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
                       
            strava_athlete_id INTEGER UNIQUE,
            client_secret TEXT,
            strava_refresh_token TEXT,
            token_expiration INTEGER
        )
        """)

        # Athlete table
        cursor.execute("""
        CREATE TABLE Athletes (
            user_id INTEGER PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            gender TEXT CHECK(gender IN ('M', 'F', 'O')) DEFAULT 'O',
            mileage_goal REAL,
            long_run_goal REAL,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
        """)

        # DailyMileage table
        cursor.execute("""
        CREATE TABLE DailyMileage (
            user_id INTEGER,
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            distance REAL,
            activity_title VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
        """)

        conn.commit()

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Unable to establish connection to {DB_NAME}")


# USER MANAGEMENT METHODS

def get_user_by_id(user_id):
    """Get user by ID. Returns row dict or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username):
    """Get user by username. Returns row dict or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username, password, strava_athlete_id, client_secret, strava_refresh_token):
    """Create a new user. Returns the new user's ID."""
    # Hash the password using werkzeug's secure hashing
    #should probably hash the tokens, but need to find a way to retrieve them later
    if check_if_user_exists(username):
        raise ValueError("User already exists")
    
    hashed_pw = generate_password_hash(password)
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO Users (username, password_hash, strava_athlete_id, client_secret, strava_refresh_token) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_pw, strava_athlete_id, client_secret, strava_refresh_token)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError as e:
        conn.close()
        # Handle race condition: two simultaneous requests could both pass existence check
        # The second INSERT will fail with IntegrityError due to UNIQUE constraint
        if 'UNIQUE constraint failed' in str(e) or 'username' in str(e).lower():
            raise ValueError("User already exists")
        else:
            # Re-raise if it's a different integrity constraint
            raise

def check_if_user_exists(username):
    """Check if a user exists in the database. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def user_has_strava(user_id):
    """Check if user has Strava tokens. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT client_secret FROM Users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None and row['client_secret'] is not None

def user_login(username, password):
    """Login a user. Returns True/False."""
    user_row = get_user_by_username(username)
    if user_row and check_password_hash(user_row['password_hash'], password):
        return True
    else:
        return False

def get_refresh_token_by_username(username):
    """Get the refresh token for a user by username. Returns the token string or None."""
    user_row = get_user_by_username(username)
    if user_row:
        return user_row.get('strava_refresh_token')
    return None

def get_client_id_from_username(username):
    user_row = get_user_by_username(username)
    return user_row['strava_athlete_id']

def get_client_secret_by_username(username):
    user_row = get_user_by_username(username)
    return user_row['client_secret']

def get_most_recent_activity_date_by_username(username):
    #will pass in session username when using this function
    conn = get_connection()
    cursor = conn.cursor()
    # Join DailyMileage directly to Users (no need for Athletes table)
    cursor.execute("SELECT d.date FROM DailyMileage d INNER JOIN Users u ON d.user_id = u.id WHERE u.username = ? ORDER BY d.date DESC LIMIT 1", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_activity_distance_by_activity_id(activity_id):
    #will be called by app.py or script.py to get the activity distance for the current day
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT distance FROM DailyMileage WHERE activity_id = ?", (activity_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_activity_distance_by_date(date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT distance FROM DailyMileage WHERE date = ?", (date,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def create_activity(user_id, date, distance, activity_title):
    #will be called when an activity is grabbed by the collector (so info is just passed in)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO DailyMileage (user_id, date, distance, activity_title) VALUES (?, ?, ?, ?)", (user_id, date, distance, activity_title))
    conn.commit()
    conn.close()

def get_user_id_from_username(username):
    user_row = get_user_by_username(username)
    return user_row['id']

def get_row_from_athletes_table(username):
    conn = get_connection()
    cursor = conn.cursor()
    user_id = get_user_id_from_username(username)
    cursor.execute("SELECT * FROM Athletes WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_athlete_at_registration(username):
    #athlete table should be updated via information acquired from the collector
    user_row = get_user_by_username(username)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Athletes (user_id) VALUES (?)", (user_row['id'],))
    conn.commit()
    conn.close()

def update_athlete_with_collector_info(username, first_name, last_name, gender):
    user_row = get_row_from_athletes_table(username)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Athletes SET first_name = ?, last_name = ?, gender = ? WHERE user_id = ?", (first_name, last_name, gender, user_row['user_id']))
    conn.commit()
    conn.close()

def set_long_run_goal(username, long_run_goal):
    user_row = get_row_from_athletes_table(username)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Athletes SET long_run_goal = ? WHERE user_id = ?", (long_run_goal, user_row['user_id']))
    conn.commit()
    conn.close()

def set_mileage_goal(username, mileage_goal):
    user_row = get_row_from_athletes_table(username)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Athletes SET mileage_goal = ? WHERE user_id = ?", (mileage_goal, user_row['user_id']))
    conn.commit()
    conn.close()

def activity_exists(user_id, date, distance, activity_title):
    """Check if an activity already exists. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT activity_id FROM DailyMileage WHERE user_id = ? AND date = ? AND distance = ? AND activity_title = ?",
        (user_id, date, distance, activity_title)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None

# def save_user_tokens(user_id, tokens):
#     """Save Strava tokens to user. tokens is a dict with access_token, refresh_token, expires_at, athlete.id"""
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute(
#         """UPDATE Users 
#            SET strava_athlete_id = ?, 
#                strava_access_token = ?, 
#                strava_refresh_token = ?, 
#                token_expiration = ?
#            WHERE id = ?""",
#         (
#             tokens.get('athlete', {}).get('id'),
#             tokens.get('access_token'),
#             tokens.get('refresh_token'),
#             tokens.get('expires_at'),
#             user_id
#         )
#     )
#     conn.commit()
#     conn.close()


# ACTIVITY METHODS

def get_activities_for_user(user_id):
    """Get all activities for a user. Returns list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT activity_id, date, distance, activity_title 
           FROM DailyMileage 
           WHERE user_id = ? 
           ORDER BY date DESC""",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

