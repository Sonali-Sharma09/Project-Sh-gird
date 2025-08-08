# Project Shāgird - Backend Server (v3.1 - Final Stable Version)
# Connected to Firebase Firestore Database

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
import random

# --- Firebase Initialization ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
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
        if performance_ratio <= 0.25: return { "level": "Foundation", "topic": "Basics of Numbers & Operations", "reason": "Your basics seem weak. Let's start from the very beginning!", "video_url": "https://www.youtube.com/embed/5n_hI1gM3-k" }
        elif performance_ratio <= 0.5: return { "level": "Beginner", "topic": "Introduction to Algebra", "reason": "You have some knowledge. This video will help you build a good foundation.", "video_url": "https://www.youtube.com/embed/5n_hI1gM3-k" }
        elif performance_ratio <= 0.75: return { "level": "Intermediate", "topic": "Solving Linear Equations", "reason": "Great job! You are ready for the next level.", "video_url": "https://www.youtube.com/embed/pURwG_dO-6k" }
        else: return { "level": "Advanced", "topic": "Introduction to Quadratic Equations", "reason": "Excellent work! Let's try a more advanced topic.", "video_url": "https://www.youtube.com/embed/iulx0z1lz8M" }
    
    elif subject == 'science':
        if performance_ratio <= 0.25: return { "level": "Foundation", "topic": "What is Science?", "reason": "Your basics seem weak. Let's start from the very beginning!", "video_url": "https://www.youtube.com/embed/UPvgl_3pT6w" }
        elif performance_ratio <= 0.5: return { "level": "Beginner", "topic": "What is Photosynthesis?", "reason": "You have some knowledge. This video will help you build a good foundation.", "video_url": "https://www.youtube.com/embed/UPvgl_3pT6w" }
        elif performance_ratio <= 0.75: return { "level": "Intermediate", "topic": "Newton's Laws of Motion", "reason": "Great job! You are ready for the next level.", "video_url": "https://www.youtube.com/embed/k5kK8h2wA48" }
        else: return { "level": "Advanced", "topic": "Basics of Electricity", "reason": "Excellent work! Let's try a more advanced topic.", "video_url": "https://www.youtube.com/embed/v1-5b_2fA6E" }
    
    return { "level": "Beginner", "topic": "Introduction", "reason": "Let's get started!", "video_url": "https://www.youtube.com/embed/5n_hI1gM3-k" }


# --- API Endpoints ---
@app.route('/')
def home():
    """Server's welcome message."""
    return jsonify({"message": "Welcome to Project Shagird's Backend API! The server is live."})

@app.route('/quiz/<subject_name>', methods=['GET'])
def get_quiz(subject_name):
    if not db: return jsonify({"error": "Database not connected"}), 500
    try:
        questions_ref = db.collection('quizzes').document(subject_name).collection('questions').stream()
        all_questions = [{'id': q.id, **q.to_dict()} for q in questions_ref]
        return jsonify(random.sample(all_questions, min(len(all_questions), 4)))
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
        correct_answers = {}
        for q in questions_ref:
            q_data = q.to_dict()
            if q_data and 'answer' in q_data: correct_answers[q.id] = q_data['answer']
        score = sum(1 for q_id, u_ans in user_answers.items() if q_id in correct_answers and str(correct_answers[q_id]) == str(u_ans))
        total_questions = len(user_answers)
        recommendation = get_ml_recommendation(score, total_questions, subject)
        result_data = { "userId": user_id, "subject": subject, "score": score, "total": total_questions, "level": recommendation['level'], "recommendation_topic": recommendation['topic'], "recommendation_reason": recommendation['reason'], "video_url": recommendation['video_url'] }
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
        progress_ref = db.collection('results').where('userId', '==', user_id).stream()
        user_results = []
        for result in progress_ref:
            res_data = result.to_dict()
            if 'timestamp' in res_data and res_data['timestamp']: res_data['timestamp'] = res_data['timestamp'].strftime('%d %b %Y, %I:%M %p')
            user_results.append(res_data)
        user_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(user_results)
    except Exception as e:
        return jsonify({"error": f"Could not fetch progress: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
