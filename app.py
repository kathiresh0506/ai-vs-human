import streamlit as st
import ollama
import firebase_admin
from firebase_admin import credentials, firestore
import time
from datetime import datetime
import pytz
import json

# Initialize Firebase using Streamlit secrets
if not firebase_admin._apps:
    firebase_config = json.loads(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)

# Firestore reference
db = firestore.client()
scores_ref = db.collection('scores')

# Score update function
def update_score(user_id, name, score):
    doc_ref = db.collection('scores').document(user_id)
    doc_ref.set({
        'name': name,
        'score': firestore.Increment(score)  # Increment the score
    }, merge=True)

# Calculate AI response similarity score
def calculate_score(user_line, ai_line):
    similarity = difflib.SequenceMatcher(None, user_line, ai_line).ratio()
    return round(similarity * 100, 2)

# Save score to Firestore
def save_score(user_id, username, score):
    doc_ref = scores_ref.document(user_id)
    
    doc = doc_ref.get()
    if doc.exists:
        current_data = doc.to_dict()
        new_score = current_data.get('Score', 0) + score  # Increment score
    else:
        new_score = score  # First-time entry

    doc_ref.set({
        'Name': username,
        'Score': new_score,
        'timestamp': datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
    }, merge=True)  # Merge ensures it updates instead of overwriting everything

# Get AI response from Ollama
def get_ai_response(prompt, short_response=False):
    response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
    full_response = response['message']['content']
    if short_response:
        return full_response.split(".")[0] + "."
    return full_response

# Function to clear text input
def clear_text():
    st.session_state["story_input"] = ""

# Initialize Streamlit page
st.set_page_config(page_title="Story Chain Game", layout="wide")
st.title("🌟 AI Story Chain Game")
st.sidebar.header("Game Settings")

# Session state setup
def initialize_session():
    default_values = {
        "username": "",
        "user_id": "",
        "story": "Once upon a time in a mystical forest, a hidden portal glowed under the moonlight.",
        "total_score": 0,
        "round": 1,
        "game_over": False,
        "start_time": time.time(),
        "missed_turns": 0,
        "submitted": False  # Flag to track if a submission has been made
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session()

# User input for name
st.session_state.username = st.sidebar.text_input("Enter your name:", st.session_state.username)

if st.sidebar.button("Start Game"):
    if st.session_state.username:
        st.session_state.user_id = st.session_state.username.replace(" ", "_").lower()
        st.session_state.round = 1
        st.session_state.total_score = 0
        st.session_state.story = "Once upon a time in a mystical forest, a hidden portal glowed under the moonlight."
        st.session_state.game_over = False
        st.session_state.start_time = time.time()
        st.session_state.submitted = False
        if "story_input" in st.session_state:
            st.session_state["story_input"] = ""
        st.success(f"Welcome, {st.session_state.username}! Let's build a story together.")
    else:
        st.warning("Please enter your name to start the game.")

# Display current story
st.subheader("Story Progress:")
st.write(st.session_state.story)

# Game rounds (3 rounds)
if not st.session_state.game_over:
    if st.session_state.round <= 3:
        st.subheader(f"Round {st.session_state.round} - Your Turn!")
        time_left = max(0, 120 - int(time.time() - st.session_state.start_time))
        st.sidebar.markdown(f"⏳ **Time Left: {time_left} sec**")

        # Check if we need to clear the input (after submission)
        if st.session_state.submitted:
            st.session_state["story_input"] = ""
            st.session_state.submitted = False

        # Use a consistent key for the text area to properly manage its state
        user_input = st.text_area("Enter your story continuation:", key="story_input")

        if time_left == 0:
            st.warning("⏰ Time's up! AI adds its line...")
            st.session_state.total_score -= 10
            st.session_state.missed_turns += 1
            ai_response = get_ai_response(st.session_state.story, short_response=True)
            st.session_state.story += " " + ai_response
            st.session_state.round += 1
            st.session_state.start_time = time.time()
            if "story_input" in st.session_state:
                st.session_state["story_input"] = ""
            st.rerun()  # Auto-refresh after AI adds response

        if st.button("Submit Response"):
            if user_input.strip():
                # Update story with user input
                st.session_state.story += " " + user_input.strip()
                
                # Get AI response
                ai_response = get_ai_response(st.session_state.story, short_response=True)
                st.session_state.story += " " + ai_response
                
                # Calculate score
                score = calculate_score(user_input.strip(), ai_response)
                st.session_state.total_score += score
                
                # Save score to Firestore
                save_score(st.session_state.user_id, st.session_state.username, st.session_state.total_score)
                
                # Increment round and reset timer
                st.session_state.round += 1
                st.session_state.start_time = time.time()
                
                # Set flag to clear input on next render
                st.session_state.submitted = True
                
                # Rerun Streamlit app
                st.rerun()
            else:
                st.warning("Please enter a line before submitting.")

    if st.session_state.round > 3:
        st.session_state.game_over = True
        save_score(st.session_state.user_id, st.session_state.username, st.session_state.total_score)
        st.success(f"🎉 Game Over! Your score: {st.session_state.total_score}/300")
        st.write(f"📊 **Performance:** {round((st.session_state.total_score / 300) * 100, 2)}%")
        if st.session_state.missed_turns > 0:
            st.warning(f"⚠️ You missed {st.session_state.missed_turns} turn(s), losing 10 points each time.")

# **Leaderboard with Auto Refresh**
st.sidebar.title("Leaderboard")

scores = scores_ref.order_by('Score', direction=firestore.Query.DESCENDING).stream()
for doc in scores:
    data = doc.to_dict()
    if 'Name' in data and 'Score' in data:
        st.sidebar.write(f"**{data['Name']}**: {data['Score']} points")

# Keep the 1-second refresh for timer updates
time.sleep(1)  
st.rerun()