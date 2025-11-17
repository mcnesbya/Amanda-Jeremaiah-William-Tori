import sys
import os
# Add parent directory to path so we can import collector
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import collector
import pytest
import datetime
from unittest.mock import patch, MagicMock

# ============================================
# Testing Database Functions (No mocking needed)
# ============================================

#command to test- pytest tests/test_collector.py::test_init_db or pytest tests/ -v


def test_init_db():
    """Test that init_db creates the database tables."""
    collector.init_db()
    
    # Verify tables exist by querying them
    import sqlite3
    with sqlite3.connect(collector.DB_NAME) as conn:
        cursor = conn.cursor()
        # Check Athletes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Athletes'")
        assert cursor.fetchone() is not None
        # Check DailyMileage table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='DailyMileage'")
        assert cursor.fetchone() is not None

def test_add_example_data():
    """Test that add_example_data adds data to the database."""
    collector.init_db()
    collector.add_example_data()
    
    # Verify data was added
    import sqlite3
    with sqlite3.connect(collector.DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Athletes")
        athlete_count = cursor.fetchone()[0]
        assert athlete_count > 0
        
        cursor.execute("SELECT COUNT(*) FROM DailyMileage")
        mileage_count = cursor.fetchone()[0]
        assert mileage_count > 0

def test_get_latest_fetch_date():
    """Test that get_latest_fetch_date returns the most recent date."""
    collector.init_db()
    collector.add_example_data()
    
    result = collector.get_latest_fetch_date()
    # Use datetime.datetime.now() - datetime is the module, datetime.datetime is the class
    projected_result = datetime.datetime.now().date().isoformat()
    assert result == projected_result
    # Should return a date string
    assert isinstance(result, str)

def test_get_latest_fetch_date_empty():
    """Test get_latest_fetch_date when table is empty."""
    collector.init_db()
    # Don't add data
    
    result = collector.get_latest_fetch_date()
    assert result is None

# ============================================
# Testing API Functions (Use mocking to avoid real API calls)
# ============================================

@patch('collector.fetch_activities_after_date')
@patch('collector.get_latest_fetch_date')
def test_fetch_new_activities(mock_get_date, mock_fetch_activities):
    """Test fetch_new_activities with mocked dependencies."""
    # Setup: Define what the mocked functions should return
    mock_get_date.return_value = "2024-01-01"
    mock_fetch_activities.return_value = [
        {"id": 1, "name": "Morning Run", "distance": 5.0}
    ]
    
    # Execute
    result = collector.fetch_new_activities()
    
    # Verify
    assert result is not None
    assert len(result) == 1
    # Verify the mocked functions were called
    mock_get_date.assert_called_once()
    mock_fetch_activities.assert_called_once_with("2024-01-01")

@patch('collector.fetch_activities_after_date')
@patch('collector.get_latest_fetch_date')
def test_fetch_new_activities_no_data(mock_get_date, mock_fetch_activities):
    """Test fetch_new_activities when there's no data in database."""
    mock_get_date.return_value = None
    
    result = collector.fetch_new_activities()
    
    assert result is None
    # Should not call fetch_activities_after_date when there's no data
    mock_fetch_activities.assert_not_called()

@patch('collector.requests.get')
@patch('collector.refresh_access_token')
@patch('collector.os.getenv')
def test_fetch_activities_after_date(mock_getenv, mock_refresh, mock_get):
    """Test fetch_activities_after_date with mocked API calls."""
    # Setup mocks
    mock_getenv.side_effect = lambda key: {
        'STRAVA_CLIENT_ID': 'test_id',
        'STRAVA_CLIENT_SECRET': 'test_secret',
        'STRAVA_REFRESH_TOKEN': 'test_token'
    }.get(key)
    mock_refresh.return_value = "fake_access_token"
    
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 1, "name": "Test Run", "distance": 5.0}
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    # Execute
    test_date = datetime.datetime(2024, 1, 1)
    result = collector.fetch_activities_after_date(test_date)
    
    # Verify
    assert result is not None
    assert len(result) == 1
    assert result[0]["name"] == "Test Run"

@patch('collector.os.getenv')
def test_fetch_activities_after_date_missing_credentials(mock_getenv):
    """Test that missing credentials raises an error."""
    mock_getenv.return_value = None  # All credentials are None
    
    with pytest.raises(ValueError, match="Missing Strava credentials"):
        collector.fetch_activities_after_date(datetime.datetime.now())

@patch('collector.requests.post')
def test_refresh_access_token(mock_post):
    """Test refresh_access_token with mocked API call."""
    # Mock the token response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'access_token': 'new_access_token_123'
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    # Execute
    result = collector.refresh_access_token('client_id', 'client_secret', 'refresh_token')
    
    # Verify
    assert result == 'new_access_token_123'
    mock_post.assert_called_once()