import database as db

db.init_global_database()  # ensure DB exists
db.set_setting("groq_api_key", "PASTE_YOUR_NEW_KEY_HERE")

print("Key saved successfully")