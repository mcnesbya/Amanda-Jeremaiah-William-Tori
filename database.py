import sqlite3
import datetime

DB_NAME = "MileageTracker.db"

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Unable to establish connection to {DB_NAME}")

def get_athletes():
    with get_connection() as conn:
        athlete_rows = conn.execute("SELECT * FROM Athletes").fetchall()

        return [dict(row) for row in athlete_rows]

def get_athlete_activities(athlete_id, conn):
    activity_rows = conn.execute(
        "SELECT * FROM DailyMileage WHERE athlete_id = ? ORDER BY date DESC",
        (athlete_id,)).fetchall()
    return [dict(row) for row in activity_rows]

def get_athletes_activities():
    with get_connection() as conn:
        conn = get_connection()
        athletes_rows = conn.execute("SELECT * FROM Athletes").fetchall()
        
        all_data = [dict(row) for row in athletes_rows]

        for athlete in all_data:
            athlete_id = athlete["athlete_id"]

            mileage_data = get_athlete_activities(athlete_id, conn)
            athlete["mileage"] = mileage_data

        return all_data

def get_all_activities():
    with get_connection() as conn:
        activity_rows = conn.execute("SELECT * FROM DailyMileage").fetchall()
        return [dict(row) for row in activity_rows]
    

    

