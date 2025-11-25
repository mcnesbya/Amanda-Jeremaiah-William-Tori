import os
import threading
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


import database  
import collector 

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
    
    # Check Password Hash
    if user_row and check_password_hash(user_row['password_hash'], password):
        user_obj = User(id=user_row['id'], username=user_row['username'])
        login_user(user_obj)
        return redirect(url_for('dashboard'))
        
    flash("Invalid credentials")
    return redirect(url_for('login_page'))

@app.route('/register', methods=['POST'])
def register_action():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Hash the password
    hashed_pw = generate_password_hash(password)
    
    # Save to DB
    try:
        # Write create_user in database.py
        new_user_id = database.create_user(username, hashed_pw)
        
        # Log them in immediately
        user_obj = User(id=new_user_id, username=username)
        login_user(user_obj)
        return redirect(url_for('dashboard'))
        
    except Exception as e:
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
    Used by script.js to draw the charts.
    """
    # Query the database for runs from the current user denoted by the login session stuff
    activities = database.get_activities_for_user(current_user.id)
    
    return jsonify(activities)

if __name__ == "__main__":
    # Ensure DB tables exist before starting
    database.init_db() 
    print("Database Started")
    # IMPORTANT: Run on port 8000 to match Strava callback
    app.run(debug=True, host='0.0.0.0', port=8000)