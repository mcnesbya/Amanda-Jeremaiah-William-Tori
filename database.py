import sqlite3
import datetime

DB_NAME = "MileageTracker.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        #Resetting the tables each time collector is run to maintain known state
        cursor.execute("DROP TABLE IF EXISTS DailyMileage")
        cursor.execute("DROP TABLE IF EXISTS Athletes")
        
        # User table
        cursor.execute("""
        CREATE TABLE Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
                       
            strava_athlete_id INTEGER UNIQUE,
            strava_access_token TEXT,
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



