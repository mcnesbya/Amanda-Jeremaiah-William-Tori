# setup_db.py
import database


# Run the setup function
print("Creating tables...")
database.init_db()
print("Done.")