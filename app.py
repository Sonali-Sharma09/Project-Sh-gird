# Project Shāgird - Backend Server (v3.2 - Secure Version)
# Connected to Firebase Firestore Database using Environment Variables

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import os
import json
from dotenv import load_dotenv

# --- Load Environment Variables ---
# This line loads the variables from your .env file
load_dotenv()

# --- Firebase Initialization ---
try:
    # Get the credentials from the environment variable
    cred_json_str = os.getenv('FIREBASE_CREDENTIALS')
    if not cred_json_str:
        raise ValueError("FIREBASE_CREDENTIALS environment variable not set.")
    
    # Convert the string back to a dictionary
    cred_dict = json.loads(cred_json_str)
    
    # Initialize Firebase with the credentials dictionary
    cred = credentials.Certificate(cred_dict)
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        
    db = firestore.client()
    print("Successfully connected to Firebase!")

except Exception as e:
    print(f"Firebase connection failed: {e}")
    db = None

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# --- SIMULATED ML MODEL (WITH VIDEO URLS) ---
def get_ml_recommendation(score, total, subject):
    if total == 0:
        performance_ratio = 0
    else:
        performance_ratio = score / total
    
    if subject == 'maths':
        if performance_ratio <= 0.25: return { "level": "Foundation", "topic": "Basics of Numbers & Operations", "reason": "Your basics seem weak. Let's start from the very beginning!", "video_url": "https://www.youtube.com/embed/H20QOceuaOM" }
        elif performance_ratio <= 0.5: return { "level": "Beginner", "topic": "Introduction to Algebra", "reason": "You have some knowledge. This video will help you build a good foundation.", "video_url": "https://www.youtube.com/embed/H20QOceuaOM" }
        elif performance_ratio <= 0.75: return { "level": "Intermediate", "topic": "Solving Linear Equations", "reason": "Great job! You are ready for the next level.", "video_url": "https://www.youtube.com/embed/va1DT5T4lfI" }
        else: return { "level": "Advanced", "topic": "Introduction to Quadratic Equations", "reason": "Excellent work! Let's try a more advanced topic.", "video_url": "https://www.youtube.com/embed/iulx0z1lz8M" }
    
    elif subject == 'science':
        if performance_ratio <= 0.25: return { "level": "Foundation", "topic": "What is Science?", "reason": "Your basics seem weak. Let's start from the very beginning!", "video_url": "https://www.youtube.com/embed/hsLxjIHHHAY" }
        elif performance_ratio <= 0.5: return { "level": "Beginner", "topic": "What is Photosynthesis?", "reason": "You have some knowledge. This video will help you build a good foundation.", "video_url": "https://www.youtube.com/embed/N1ZJe_-i0dg" }
        elif performance_ratio <= 0.75: return { "level": "Intermediate", "topic": "Newton's Laws of Motion", "reason": "Great job! You are ready for the next level.", "video_url": "https://www.youtube.com/embed/OxA-bqDPK74" }
        else: return { "level": "Advanced", "topic": "Basics of Electricity", "reason": "Excellent work! Let's try a more advanced topic.", "video_url": "https://www.youtube.com/embed/JY24andAvME" }
    
    return { "level": "Beginner", "topic": "Introduction", "reason": "Let's get started!", "video_url": "https://www.youtube.com/embed/5n_hI1gM3-k" }


# --- API Endpoints ---
@app.route('/quiz/<subject_name>', methods=['GET'])
def get_quiz(subject_name):
    if not db: return jsonify({"error": "Database not connected"}), 500
    try:
        questions_ref = db.collection('quizzes').document(subject_name).collection('questions').stream()
        all_questions = [{'id': q.id, **q.to_dict()} for q in questions_ref]
        # Ensure we don't try to sample more questions than available
        sample_size = min(len(all_questions), 4)
        return jsonify(random.sample(all_questions, sample_size))
    except Exception as e:
        return jsonify({"error": f"Could not fetch questions: {e}"}), 500

@app.route('/submit', methods=['POST'])
def submit_quiz():
    if not db: return jsonify({"error": "Database not connected"}), 500
    try:
        data = request.get_json()
        user_answers, subject, user_id = data.get('answers'), data.get('subject'), data.get('userId')
        if not all([user_answers, subject, user_id]): return jsonify({"error": "Invalid submission data"}), 400
        
        questions_ref = db.collection('quizzes').document(subject).collection('questions').stream()
        correct_answers = {q.id: q.to_dict().get('answer') for q in questions_ref if q.to_dict() and 'answer' in q.to_dict()}
        
        score = sum(1 for q_id, u_ans in user_answers.items() if q_id in correct_answers and str(correct_answers[q_id]) == str(u_ans))
        total_questions = len(user_answers)
        
        recommendation = get_ml_recommendation(score, total_questions, subject)
        
        result_data = { 
            "userId": user_id, 
            "subject": subject, 
            "score": score, 
            "total": total_questions, 
            "level": recommendation['level'], 
            "recommendation_topic": recommendation['topic'], 
            "recommendation_reason": recommendation['reason'], 
            "video_url": recommendation['video_url'] 
        }
        
        # Prepare data for Firestore (without video_url and with timestamp)
        db_data = result_data.copy()
        db_data.pop("video_url", None)
        db_data["timestamp"] = firestore.SERVER_TIMESTAMP
        
        db.collection('results').add(db_data)
        
        return jsonify(result_data)
    except Exception as e:
        return jsonify({"error": f"Could not process submission: {e}"}), 500

@app.route('/my-progress/<user_id>', methods=['GET'])
def get_my_progress(user_id):
    if not db: return jsonify({"error": "Database not connected"}), 500
    try:
        # Query results for the specific user
        progress_ref = db.collection('results').where('userId', '==', user_id).stream()
        user_results = []
        for result in progress_ref:
            res_data = result.to_dict()
            # Safely format the timestamp if it exists
            if 'timestamp' in res_data and res_data['timestamp']:
                # Timestamps from Firestore are datetime objects
                res_data['timestamp'] = res_data['timestamp'].strftime('%d %b %Y, %I:%M %p')
            user_results.append(res_data)
        
        # Sort results by timestamp in descending order (newest first)
        # We need a default value for sorting in case timestamp is missing
        user_results.sort(key=lambda x: x.get('timestamp', '1970-01-01T00:00:00'), reverse=True)
        
        return jsonify(user_results)
    except Exception as e:
        return jsonify({"error": f"Could not fetch progress: {e}"}), 500

if __name__ == '__main__':
    # Use os.getenv to get port, default to 5000 if not set
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
