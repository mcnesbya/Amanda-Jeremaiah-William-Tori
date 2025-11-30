import os
import threading
import logging
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


import database  
import collector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-for-testing')

# FLASK LOGIN STUFF

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    """
    The 'Backpack' class. It wraps the database row so Flask-Login can read it.
    """
    def __init__(self, id, username, first_name=None):
        self.id = id
        self.username = username
        self.first_name = first_name

@login_manager.user_loader
def load_user(user_id):
    """
    Flask asks: 'I have ID 5. Who is this?'
    We ask the Database: 'Give me the row for ID 5.'
    """
    # write the db helper function
    user_row = database.get_user_by_id(user_id)
    
    if user_row:
        # Convert DB row to User object
        return User(id=user_row['id'], username=user_row['username'])
    return None


# FRONTEND ROUTING

@app.route('/')
@login_required
def dashboard():
    """
    The Main Dashboard.
    If they have Strava connected, show the charts.
    If not, show the 'Connect Strava' button.
    """
    # Check if this user has strava tokens in the DB
    has_strava = database.user_has_strava(current_user.id)
    
    return render_template('index.html', user=current_user, has_strava=has_strava)

# @app.route('/dummy_redirect')
# def dummy_redirect():
#     return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

# MORE LOGIN STUFF

@app.route('/login', methods=['POST'])
def login_action():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Check DB for username
    user_row = database.get_user_by_username(username)
    is_a_user = database.user_login(username, password) #returns True if user exists and password is correct, False if not
    
    # Check Password Hash
    if user_row and is_a_user:
        user_obj = User(id=user_row['id'], username=user_row['username'])
        login_user(user_obj)
        
        # Sync activities in background thread (non-blocking)
        def sync_activities():
            try:
                date = database.get_most_recent_activity_date_by_username(username)
                if date:
                    collector.add_new_activities_to_db(username, date)
                    logger.info(f"Successfully synced new activities for user: {username}")
                else:
                    collector.add_initial_activities_to_db(username)
                    logger.info(f"Successfully synced initial activities for user: {username}")
            except Exception as e:
                # Log error but don't prevent login
                logger.error(f"Error syncing activities for {username}: {e}", exc_info=True)
        
        # Start sync in background thread
        sync_thread = threading.Thread(target=sync_activities)
        sync_thread.start()
        
        flash("Logged in successfully. Activity sync in progress...", "info")
        return redirect(url_for('dashboard'))
        
    flash("Invalid credentials")
    return redirect(url_for('login_page'))

@app.route('/register', methods=['POST'])
def register_action():
    username = request.form.get('username')
    password = request.form.get('password')
    strava_athlete_id = request.form.get('stravaAthleteId')
    strava_access_token = request.form.get('stravaAccessToken')
    strava_refresh_token = request.form.get('stravaRefreshToken')
    
    # Save to DB (password will be hashed inside create_user)
    try:
        new_user_id = database.create_user(
            username, 
            password,  # Plain password - will be hashed in database.py
            strava_athlete_id,
            strava_access_token,
            strava_refresh_token
        )
        
        # Log them in immediately
        user_obj = User(id=new_user_id, username=username)
        login_user(user_obj)
        
        # Sync athlete info and activities in background thread (non-blocking)
        def sync_strava_data():
            try:
                logger.info(f"=== Starting Strava sync for user: {username} ===")
                
                # Create athlete row first if it doesn't exist
                athlete_row = database.get_row_from_athletes_table(username)
                if not athlete_row:
                    logger.info(f"Creating athlete row for user: {username}")
                    database.create_athlete_at_registration(username)
                else:
                    logger.info(f"Athlete row already exists for user: {username}")
                
                # Verify credentials exist before proceeding
                client_id = database.get_client_id_from_username(username)
                client_secret = database.get_client_secret_by_username(username)
                refresh_token = database.get_refresh_token_by_username(username)
                
                logger.info(f"Credentials check - client_id: {client_id}, has_secret: {bool(client_secret)}, has_refresh: {bool(refresh_token)}")
                
                if not all([client_id, client_secret, refresh_token]):
                    raise ValueError(f'Missing Strava credentials - client_id: {bool(client_id)}, secret: {bool(client_secret)}, refresh: {bool(refresh_token)}')
                
                # Try to update athlete info (non-blocking - if it fails, continue to activities)
                try:
                    logger.info(f"Updating athlete info for user: {username}")
                    collector.update_athlete_info_in_db(username)
                    logger.info(f"Successfully updated athlete info for user: {username}")
                except Exception as e:
                    logger.warning(f"Failed to update athlete info for {username}: {e}. Continuing to fetch activities...")
                
                # Fetch activities (this is the important part)
                logger.info(f"Fetching initial activities for user: {username}")
                collector.add_initial_activities_to_db(username)
                logger.info(f"Successfully synced initial activities for user: {username}")
                logger.info(f"=== Completed Strava sync for user: {username} ===")
            except Exception as e:
                # Log error but don't prevent registration/login
                logger.error(f"ERROR syncing Strava data for {username}: {e}", exc_info=True)
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                print(f"ERROR in background thread: {e}")
                print(traceback.format_exc())
        
        # Start sync in background thread
        sync_thread = threading.Thread(target=sync_strava_data, daemon=True)
        sync_thread.start()
        logger.info(f"Started background thread for Strava sync (thread ID: {sync_thread.ident})")
        print(f"DEBUG: Started background thread for user: {username}")
        
        flash("Registration successful! Syncing your Strava data...", "info")
        return redirect(url_for('dashboard'))
        
    except ValueError as e:
        # User already exists or other validation error
        # Check if this is a fetch request (by checking if Accept header includes json or if it's an XHR)
        accepts_json = 'application/json' in request.headers.get('Accept', '')
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if accepts_json or is_xhr:
            return jsonify({'error': str(e)}), 400
        flash(f"Error: {e}")
        return redirect(url_for('register_page'))
    except Exception as e:
        # Other errors
        accepts_json = 'application/json' in request.headers.get('Accept', '')
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if accepts_json or is_xhr:
            return jsonify({'error': str(e)}), 500
        flash(f"Error: {e}")
        return redirect(url_for('register_page'))

@app.route('/logout')
@login_required
def logout_action():
    logout_user()
    return redirect(url_for('login_page'))

# STRAVA INTEGRATION STUFF

@app.route('/connect/strava')
@login_required
def connect_strava():
    """
    Redirects the user to Strava.com to authorize our app.
    """
    client_id = os.getenv('STRAVA_CLIENT_ID')
    redirect_uri = "http://localhost:8000/strava/callback"
    
    # Construct the URL
    strava_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&approval_prompt=force&scope=read,activity:read_all"
    
    return redirect(strava_url)

@app.route('/strava/callback')
@login_required
def strava_callback():
    """
    Strava sends them back here with a code.
    We swap code for tokens -> Save to DB -> Start Thread.
    """
    code = request.args.get('code')
    
    if code:
        tokens = collector.exchange_code_for_tokens(code)
        
        database.save_user_tokens(current_user.id, tokens)
        
        # This lets the user go to the dashboard while we download runs in background
        sync_thread = threading.Thread(
            target=collector.fetch_and_save_user_data,
            args=(current_user.id,)
        )
        sync_thread.start()
        
        flash("Connected! Syncing your runs now...")
        return redirect(url_for('dashboard'))
    
    return "Error: No code received from Strava"



@app.route('/api/activities')
@login_required
def get_activities_data():
    """
    API endpoint for dashboard data.
    Returns all activities, mileage goal, and long run goal for the current user as JSON.
    Used by script.js to populate the mileage tracker.
    """
    # Get current user's activities from database
    activities = database.get_activities_for_user(current_user.id)
    logger.info(f"API: Returning {len(activities)} activities for user: {current_user.username} (ID: {current_user.id})")
    
    # Get mileage goal and long run goal from Athletes table
    athlete_row = database.get_row_from_athletes_table(current_user.username)
    mileage_goal = athlete_row.get('mileage_goal', 0) if athlete_row else 0
    long_run_goal = athlete_row.get('long_run_goal', 0) if athlete_row else 0
    
    # Return JSON response with activities and goals
    return jsonify({
        'activities': activities,
        'mileage_goal': mileage_goal,
        'long_run_goal': long_run_goal
    })

@app.route('/api/debug/sync')
@login_required
def manual_sync():
    """
    Debug endpoint to manually trigger Strava sync.
    Useful for testing if background thread isn't working.
    """
    username = current_user.username
    logger.info(f"Manual sync triggered for user: {username}")
    
    try:
        # Create athlete row first if it doesn't exist
        athlete_row = database.get_row_from_athletes_table(username)
        if not athlete_row:
            logger.info(f"Creating athlete row for user: {username}")
            database.create_athlete_at_registration(username)
        
        # Verify credentials exist
        client_id = database.get_client_id_from_username(username)
        client_secret = database.get_client_secret_by_username(username)
        refresh_token = database.get_refresh_token_by_username(username)
        
        if not all([client_id, client_secret, refresh_token]):
            return jsonify({
                'error': 'Missing Strava credentials',
                'has_client_id': bool(client_id),
                'has_secret': bool(client_secret),
                'has_refresh': bool(refresh_token)
            }), 400
        
        # Update athlete info and fetch activities
        collector.update_athlete_info_in_db(username)
        collector.add_initial_activities_to_db(username)
        
        # Get updated activities count
        activities = database.get_activities_for_user(current_user.id)
        
        return jsonify({
            'success': True,
            'activities_count': len(activities),
            'message': f'Successfully synced {len(activities)} activities'
        })
    except Exception as e:
        logger.error(f"Error in manual sync: {e}", exc_info=True)
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

if __name__ == "__main__":
    # Ensure DB tables exist before starting
    database.init_db() 
    print("Database Started")
    # IMPORTANT: Run on port 8000 to match Strava callback
    app.run(debug=True, host='0.0.0.0', port=8000)