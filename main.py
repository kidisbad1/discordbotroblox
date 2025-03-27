import requests
import time
from datetime import datetime
import pytz  
from flask import Flask
import threading

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def hello():
    return "Service is running!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)  # Bind to port 10000

# Run Flask in a separate thread so your main script can continue running
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# Your existing script continues here

USER_IDS = [4236892758, 5657262735, 1199584082, 1534478137]  #User IDs

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1353893904243621908/4088jg5I0xd8Kr9rW1AuYVxSRuVecwYJRCne6R-nSD4zMjHto344sgSgj16llOx1mxlz"

# APIs
ROBLOX_PRESENCE_API = "https://presence.roblox.com/v1/presence/users"
ROBLOX_USER_API = "https://users.roblox.com/v1/users/{user_id}"

last_status = {}
game_start_time = {}  
game_join_time_str = {}  
current_game = {}  
last_online_status_sent = {}  

# (EDT)
edt = pytz.timezone("America/New_York")

# display name
def get_roblox_display_name(user_id):
    try:
        response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
        if response.status_code == 200:
            return response.json().get("displayName", "Unknown User")
    except Exception as e:
        print(f"❌ Error fetching username: {e}")
    return "Unknown User"

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"

# EDT
def current_time():
    return datetime.now(edt).strftime("%I:%M %p")  

# user's display name
user_display_names = {user_id: get_roblox_display_name(user_id) for user_id in USER_IDS}

print(f"🔍 Tracking Roblox users: {', '.join([str(user_id) for user_id in USER_IDS])}... (Press CTRL+C to stop)")

while True:
    try:
        response = requests.post(
            ROBLOX_PRESENCE_API,
            json={"userIds": USER_IDS},
            headers={"Content-Type": "application/json"}
        )

        data = response.json()

        if "userPresences" in data and len(data["userPresences"]) > 0:
            for presence_data in data["userPresences"]:
                user_id = presence_data["userId"]
                display_name = user_display_names.get(user_id, "Unknown User")
                presence_type = presence_data.get("userPresenceType", 0)  
                game = presence_data.get("lastLocation", "")

                if user_id not in last_status:
                    last_status[user_id] = None
                    game_start_time[user_id] = None
                    game_join_time_str[user_id] = None
                    current_game[user_id] = None
                    last_online_status_sent[user_id] = False

                status = ""

                if presence_type == 0:
                    status = f"🚪 **{display_name} went offline!**"
                    if game_start_time[user_id]:  
                        time_in_game = time.time() - game_start_time[user_id]
                        leave_time_str = current_time()
                        status += f" ⏳ **They played {current_game[user_id]} from {game_join_time_str[user_id]} to {leave_time_str} ({format_time(time_in_game)}).**"
                        game_start_time[user_id] = None 
                        current_game[user_id] = None
                    last_online_status_sent[user_id] = False  

                elif presence_type == 1:
                    if not last_online_status_sent[user_id]: 
                        status = f"💻 **{display_name} is online but not in a game.**"
                        if game_start_time[user_id]:
                            time_in_game = time.time() - game_start_time[user_id]
                            leave_time_str = current_time()
                            status += f" ⏳ **They played {current_game[user_id]} from {game_join_time_str[user_id]} to {leave_time_str} ({format_time(time_in_game)}).**"
                            game_start_time[user_id] = None  
                            current_game[user_id] = None
                        last_online_status_sent[user_id] = True  

                elif presence_type == 2:
                    if game:
                        status = f"🎮 **{display_name} joined:** {game} at **{current_time()} EDT**"
                    else:
                        status = f"🎮 **{display_name} is in a game, but the game name is not available.**"

                    if current_game[user_id] and current_game[user_id] != game:
                        time_in_game = time.time() - game_start_time[user_id]
                        leave_time_str = current_time()
                        status += f"\n🚪 **{display_name} left {current_game[user_id]} at {leave_time_str} EDT, played for {format_time(time_in_game)}.**"
                        game_start_time[user_id] = time.time() 
                        game_join_time_str[user_id] = current_time()  

                    if game_start_time[user_id] is None:
                        game_start_time[user_id] = time.time()
                        game_join_time_str[user_id] = current_time()  

                    current_game[user_id] = game  
                    last_online_status_sent[user_id] = False  

                if status and status != last_status[user_id]:
                    last_status[user_id] = status
                    discord_payload = {"content": status}
                    discord_response = requests.post(DISCORD_WEBHOOK_URL, json=discord_payload)

                    print(f"Discord Response: {discord_response.status_code} {discord_response.text}")
                    print(status)

    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(5)
