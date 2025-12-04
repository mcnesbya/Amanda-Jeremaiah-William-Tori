import os
import threading
import logging
import time
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import database
import collector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# FLASK LOGIN STUFF

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, id, username, last_sync_time=0 ):
        self.id = id
        self.username = username
        self.last_sync_time = last_sync_time
        

@login_manager.user_loader
def load_user(user_id):
    user_row = database.get_user_by_id(user_id)
    
    if user_row:
        return User(id=user_row['id'], username=user_row['username'],last_sync_time=user_row['last_sync_time'])
    return None

# FRONTEND ROUTING

@app.route('/')
@login_required
def dashboard():
    current_time = time.time()
    last_sync = current_user.last_sync_time
    has_strava = database.user_has_strava(current_user.id)

    if current_time - last_sync > 900:
        sync_thread = threading.Thread(
            target=collector.fetch_and_save_user_data,
            args=(current_user.id,)
        )
        sync_thread.start()

        database.update_last_sync_time(current_user.id)
    
    
    return render_template('index.html', user=current_user, has_strava=has_strava)

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
    is_valid_password = database.validate_password(username, password)
    
    # Check Password Hash
    if user_row and is_valid_password:
        user_obj = User(id=user_row['id'], username=user_row['username'])
        login_user(user_obj)

        return redirect(url_for('dashboard'))
        
    flash("Invalid credentials")
    return redirect(url_for('login_page'))

@app.route('/register', methods=['POST'])
def register_action():
    username = request.form.get('username')
    password = request.form.get('password')
    mileage_goal = request.form.get('mileage')
    long_run_goal = request.form.get('long_run')
    
    # Save to DB (password will be hashed inside create_user)
    try:
        new_user_id = database.create_user(
            username, 
            password
        )
        
        # Create athlete record with goals
        if mileage_goal and long_run_goal:
            try:
                mileage_goal = float(mileage_goal)
                long_run_goal = float(long_run_goal)
                database.create_athlete_with_goals(new_user_id, mileage_goal, long_run_goal)
            except (ValueError, TypeError) as e:
                print(f"Error parsing goals: {e}")
                # Continue with registration even if goals fail
        
        # Log them in immediately
        user_obj = User(id=new_user_id, username=username)
        login_user(user_obj)
        
        return redirect(url_for('dashboard'))
        
    except ValueError as e:
        print(str(e))
        return redirect(url_for('register_page'))
    
    except Exception as e:
        print(str(e))
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
    if request.args.get('error') == 'access_denied':
        flash("Connection cancelled")
        return redirect(url_for('dashboard'))

    code = request.args.get('code')

    if not code:
        flash("No code recieved")
    
    try:
        collector.authorize_and_save_user(code, current_user.id)

        sync_thread = threading.Thread(
            target=collector.fetch_and_save_user_data,
            args=(current_user.id,)
        )
        sync_thread.start()
        database.update_last_sync_time(current_user.id)
        
        flash("Connected! Syncing your runs now...")
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"OAuth failed: {e}")
        return redirect(url_for('dashboard'))


#Returns all activities, mileage goal, and long run goal for the current user as JSON.
@app.route('/api/activities')
@login_required
def get_activities_data():
    activities = database.get_activities_for_user(current_user.id)
    logger.info(f"API: Returning {len(activities)} activities for user: {current_user.username} (ID: {current_user.id})")
    
    athlete_row = database.get_row_from_athletes_table(current_user.id)
    mileage_goal = athlete_row.get('mileage_goal', 0) if athlete_row else 0
    long_run_goal = athlete_row.get('long_run_goal', 0) if athlete_row else 0
    has_strava = database.user_has_strava(current_user.id)
    
    return jsonify({
        'activities': activities,
        'mileage_goal': mileage_goal,
        'long_run_goal': long_run_goal,
        'has_strava' : has_strava
    })

if __name__ == "__main__":
    database.init_db() 
    print("Database Started")
    app.run(debug=True, host='0.0.0.0', port=8000)