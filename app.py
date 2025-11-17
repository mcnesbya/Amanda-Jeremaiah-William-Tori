from flask import Flask, jsonify, render_template
from collector import init_db, add_example_data, get_strava_athlete_info, add_strava_athlete_to_db, fetch_new_activities, add_new_activities_to_db
from database import get_athletes_activities, get_connection, get_athlete_activities, get_athletes, get_all_activities

app = Flask(__name__)

@app.route("/")
def website():
    return render_template("index.html")

@app.route("/data")
def get_data():
    try:
        add_strava_athlete_to_db()
        activities = fetch_new_activities()
        athletes = get_athletes()
        add_new_activities_to_db(activities, athletes[0]['athlete_id'])
        data = get_all_activities()
        return jsonify(data)
    except Exception as e:
        return jsonify({"Error": str(e)}), 500

@app.route("/activitiesFromID")
def get_activities_from_id():
    try:
        id = 1
        conn = get_connection()
        data = get_athlete_activities(id, conn)
        return jsonify(data)
    except Exception as e:
        return jsonify({"Error": str(e)}), 500

@app.route("/tori")
#this needs to render index.html with the data from the database for the athlete named tori (with id 2)
#after i add myself into the database
#needs to make sure all my activities are up to date in the database, so call to check (from collector)
#then call the database.py functions needed to extract that data
#then render index.html with the data
def tori():
    try: 
        tori_data = get_strava_athlete_info()
        add_strava_athlete_to_db()
        athletes = get_athletes()
        activities = fetch_new_activities()
        add_new_activities_to_db(activities, athletes[0]['athlete_id'])
        activities2 = get_all_activities()
        return jsonify(activities2)
    except Exception as e:
        return jsonify({"Error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    add_example_data()
    print("Database started")
    app.run(debug=True,port=8000)
