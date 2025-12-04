import sqlite3
import datetime
import time
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "MileageTracker.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        #Resetting the tables each time collector is run to maintain known state
        #these 3 lines will be commented out when we are done testing
        #cursor.execute("DROP TABLE IF EXISTS Users")
        #cursor.execute("DROP TABLE IF EXISTS DailyMileage")
        #cursor.execute("DROP TABLE IF EXISTS Athletes")
        
        # User table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
                       
            strava_athlete_id INTEGER UNIQUE,
            strava_access_token TEXT,
            strava_refresh_token TEXT,
            token_expiration INTEGER,
            last_sync_time INTEGER DEFAULT 0
        )
        """)

        # Athlete table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS  Athletes (
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
        CREATE TABLE IF NOT EXISTS  DailyMileage (
            user_id INTEGER,
            activity_id INTEGER PRIMARY KEY,
            date DATE,
            distance REAL,
            activity_title VARCHAR(100),
            FOREIGN KEY (user_id) REFERENCES Users(id),
            UNIQUE(user_id, date, activity_title)
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

def update_last_sync_time(user_id):
    current_time = int(time.time())
    conn = get_connection()
    cursor = conn.cursor()
    conn.execute(
        "UPDATE Users SET last_sync_time = ? WHERE id = ?", 
        (current_time, user_id)
    )
    conn.commit()
    conn.close()

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


def create_user(username, password):
    """Create a new user. Returns the new user's ID."""
    # Hash the password using werkzeug's secure hashing
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO Users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
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

def user_has_strava(user_id):
    """Check if user has Strava tokens. Returns True/False."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT strava_access_token FROM Users WHERE id = ?",
        [user_id]
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] is not None

def validate_password(username, password):
    """Login a user. Returns True/False."""
    user_row = get_user_by_username(username)
    if user_row and check_password_hash(user_row['password_hash'], password):
        return True
    else:
        return False

def get_user_tokens(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT strava_access_token, strava_refresh_token, token_expiration FROM Users WHERE id = ?", 
        (user_id,)
    ).fetchone()
    conn.close()
    return row

def update_user_tokens(user_id, access_token, refresh_token, expires_at):
    conn = get_connection()
    conn.execute(
        """UPDATE Users 
           SET strava_access_token = ?, 
               strava_refresh_token = ?, 
               token_expiration = ?
           WHERE id = ?""",
        (access_token, refresh_token, expires_at, user_id)
    )
    conn.commit()
    conn.close()

def save_user_tokens_and_info(user_id, access_token, refresh_token, expires_at, strava_id, first_name, last_name, gender):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """UPDATE Users 
           SET strava_athlete_id = ?, 
               strava_access_token = ?, 
               strava_refresh_token = ?, 
               token_expiration = ?
           WHERE id = ?""",
        (strava_id, access_token, refresh_token, expires_at, user_id)
    )

    cursor.execute(
        """INSERT OR REPLACE INTO Athletes (user_id, first_name, last_name, gender)
           VALUES (?, ?, ?, ?)""",
        (user_id, first_name, last_name, gender)
    )

    conn.commit()
    conn.close()
    print(f"Tokens and profile info saved for User ID: {user_id}")

def create_activity(user_id, date, distance, title):
    #will be called when an activity is grabbed by the collector (so info is just passed in)
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO DailyMileage (user_id, date, distance, activity_title) VALUES (?, ?, ?, ?)", 
        (user_id, date, distance, title)
    )
    conn.commit()
    conn.close()

def get_row_from_athletes_table(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Athletes WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

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
