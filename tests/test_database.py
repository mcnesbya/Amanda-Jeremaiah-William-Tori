import sys
import os
# Add parent directory to path so we can import collector
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import database
import pytest
import datetime
from unittest.mock import patch, MagicMock

# ============================================
# Testing Database Functions (No mocking needed)
# ============================================

#command to test- pytest tests/test_collector.py::test_init_db or pytest tests/ -v


def test_init_db():
    """Test that init_db creates the database tables."""
    database.init_db()
    
    # Verify tables exist by querying them
    import sqlite3
    with sqlite3.connect(database.DB_NAME) as conn:
        cursor = conn.cursor()
        # Check Athletes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Athletes'")
        assert cursor.fetchone() is not None
        # Check DailyMileage table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='DailyMileage'")
        assert cursor.fetchone() is not None

def test_create_user():
    """Test that create_user creates a new user in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testkey', 'testrefresh')
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users")
    user_row = cursor.fetchone()
    assert user_row is not None, "User should be created in database"
    assert database.get_user_by_username('testuser') is not None

def test_create_duplicate_user():
    """Test that create_user creates a new user and prevents duplicates."""
    # Initialize database to ensure clean state
    database.init_db()
    
    # Test 1: Create a new user successfully
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    
    # Verify user was created in the database
    import sqlite3
    with sqlite3.connect(database.DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", ('testuser',))
        user_row = cursor.fetchone()
        assert user_row is not None, "User should be created in database"
    
    with pytest.raises(ValueError, match="User already exists"):
        database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    
    with sqlite3.connect(database.DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ?", ('testuser',))
        count = cursor.fetchone()[0]
        assert count == 1, "Should only have one user with this username"
        
def test_check_if_user_exists():
    """Test that check_if_user_exists returns True if user exists, False if not."""
    assert database.check_if_user_exists('testuser') is True
    assert database.check_if_user_exists('nonexistentuser') is False

def test_user_login():
    """Test that user_login returns True if user exists and password is correct, False if not."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    assert database.user_login('testuser', 'testpassword') is True
    assert database.user_login('testuser', 'wrongpassword') is False

def test_session_username_set():
    """Test that the session username is set correctly."""
    #idk if you can test this
    #might be a test for the app.py file
    pass

def test_get_refresh_token_by_username():
    """Test that the get_refresh_token_by_username function returns the correct refresh token."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    assert database.get_refresh_token_by_username('testuser') == 'testrefresh'

def test_get_client_id_from_username():
    """Test that the get_client_id_from_username function returns the correct client id."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    assert database.get_client_id_from_username('testuser') == 1234567890

def test_get_most_recent_activity_date_by_username():
    """Test that the get_most_recent_activity_date_by_username function returns the correct most recent activity date."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_activity(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity')
    assert database.get_most_recent_activity_date_by_username('testuser') == '2025-01-01'

def test_get_user_id_from_username():
    """Test that the get_user_id_from_username function returns the correct user id."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    assert database.get_user_id_from_username('testuser') == 1

def test_create_activity():
    """Test that the create_activity function creates a new activity in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_activity(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity')
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM DailyMileage")
    activity_row = cursor.fetchone()
    assert activity_row is not None, "Activity should be created in database"

def test_get_row_from_atheletes_table():
    """Test that the get_row_from_athletes_table function returns the correct row from the athletes table."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_athlete_at_registration('testuser')
    assert database.get_row_from_athletes_table('testuser') is not None

def test_create_athlete_at_registration():
    """Test that the create_athlete_at_registration function creates a new athlete in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_athlete_at_registration('testuser')
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Athletes")
    athlete_row = cursor.fetchone()
    assert athlete_row is not None, "Athlete should be created in database"

def test_update_athlete_with_dummy_collector_info():
    """Test that the update_athlete_with_collector_info function updates the athlete in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_athlete_at_registration('testuser')
    #will later be called when collector info is grabbed
    database.update_athlete_with_collector_info('testuser', 'John', 'Doe', 'M')
    assert database.get_row_from_athletes_table('testuser') is not None
    assert database.get_row_from_athletes_table('testuser')['first_name'] == 'John'
    assert database.get_row_from_athletes_table('testuser')['last_name'] == 'Doe'
    assert database.get_row_from_athletes_table('testuser')['gender'] == 'M'

def test_set_long_run_goal():
    """Test that the set_long_run_goal function sets the long run goal in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_athlete_at_registration('testuser')
    database.set_long_run_goal('testuser', 100)
    assert database.get_row_from_athletes_table('testuser') is not None
    assert database.get_row_from_athletes_table('testuser')['long_run_goal'] == 100

def test_set_mileage_goal():
    """Test that the set_mileage_goal function sets the mileage goal in the database."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_athlete_at_registration('testuser')
    database.set_mileage_goal('testuser', 1000)
    assert database.get_row_from_athletes_table('testuser') is not None
    assert database.get_row_from_athletes_table('testuser')['mileage_goal'] == 1000

def test_get_activity_distance_by_activity_id():
    """Test that the get_activity_distance function returns the correct activity distance."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_activity(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity')
    assert database.get_activity_distance_by_activity_id(1) == 10.0

def test_get_activity_distance_by_date():
    """Test that the get_activity_distance_by_date function returns the correct activity distance."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_activity(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity')
    assert database.get_activity_distance_by_date('2025-01-01') == 10.0

def test_activity_exists():
    """Test that the activity_exists function returns True if the activity exists, False if not."""
    database.init_db()
    database.create_user('testuser', 'testpassword', 1234567890, 'testaccess', 'testrefresh')
    database.create_activity(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity')
    assert database.activity_exists(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity') is True
    assert database.activity_exists(database.get_user_id_from_username('testuser'), '2025-01-01', 10.0, 'testactivity2') is False