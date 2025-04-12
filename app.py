import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_bcrypt import Bcrypt 
from functools import wraps
from datetime import datetime
import logging 
import os
import streamlit as st

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_replace_this'

st.link_button("🗕 Track Learner Progress", "https://learnerprogress-dgvveudggyibgsjvbqmwhe.streamlit.app/")
st.link_button("💬 Forum (Community Q&A)", "https://crafttechniqueforum-fc77frqqlj6f2a6aczylgw.streamlit.app/")
st.link_button("🏩 Marketplace", "https://learner-marketplace.onrender.com/")


try:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", 'serviceAccountKey.json')
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    db = None

try:
    import video_content
except ImportError:
    logging.error("Could not import video_content.py. Make sure it's in the correct path.")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
if not HF_API_TOKEN:
     logging.warning("HF_API_TOKEN environment variable not set. Video processing will likely fail.")

def login_required(f):
    """Decorator to ensure user is logged in via session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: 
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('signin')) 
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorator to ensure user has the required role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                flash("Please log in.", "warning")
                return redirect(url_for('signin'))
            if session['user_role'] != required_role:
                flash(f"Access Denied: {required_role.capitalize()}s Only!", "danger")
                # Redirect to a relevant page based on role or home
                if session['user_role'] == 'learner':
                    return redirect(url_for('learner_dashboard'))
                elif session['user_role'] == 'mentor':
                     return redirect(url_for('mentor_dashboard'))
                else:
                     return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def find_and_link_learners(new_course_doc_ref, mentor_data):
    """
    Finds learners matching the mentor's skill/availability and links the new course.
    Args:
        new_course_doc_ref: Firestore DocumentReference of the newly added course.
        mentor_data (dict): Dictionary containing mentor's profile data (uid, primaryskill, availableDay, availableTime).
    """
    if not db:
        logging.error("Database unavailable, cannot perform learner matching.")
        return

    mentor_skill = mentor_data.get('primaryskill')
    mentor_day = mentor_data.get('availableDay')
    mentor_time = mentor_data.get('availableTime')
    mentor_id = mentor_data.get('uid')
    new_course_id = new_course_doc_ref.id

    if not all([mentor_skill, mentor_day, mentor_time, mentor_id, new_course_id]):
        logging.warning(f"Incomplete mentor data or course ID for matching. Mentor: {mentor_id}, Course: {new_course_id}. Skipping link.")
        return

    logging.info(f"Matching learners for Mentor {mentor_id} (Skill: {mentor_skill}, Day: {mentor_day}, Time: {mentor_time}) for Course {new_course_id}")

    try:
        learners_ref = db.collection('learners')
        query = learners_ref.where('skillinterest', '==', mentor_skill) \
                            .where('preferreddays', '==', mentor_day) \
                            .where('preferredtime', '==', mentor_time)

        matched_learners = query.stream()
        link_count = 0

        for learner_doc in matched_learners:
            learner_id = learner_doc.id
            try:
                # Add the new course ID to the learner's matched list
                learner_doc.reference.update({
                    'matched_course_ids': firestore.ArrayUnion([new_course_id])
                })
                link_count += 1
                logging.info(f"Linked Course {new_course_id} to Learner {learner_id}")
                # Optional: Send notification to learner here (e.g., via email or in-app)
                # send_new_course_notification(learner_doc.to_dict(), new_course_doc_ref.get().to_dict())
            except Exception as update_e:
                logging.error(f"Failed to link Course {new_course_id} to Learner {learner_id}: {update_e}", exc_info=True)

        logging.info(f"Finished matching for Course {new_course_id}. Linked to {link_count} learners.")

    except Exception as e:
        logging.error(f"Error querying or linking learners for Mentor {mentor_id}, Course {new_course_id}: {e}", exc_info=True)

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user registration."""
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        selected_role = request.form.get('role')

        if not all([fullname, email, password, selected_role]):
            flash("All fields including role are required.", "danger")
            return redirect(url_for('signup'))

        if selected_role not in ["mentor", "learner"]:
             flash("Invalid role selected.", "danger")
             return redirect(url_for('signup'))

        try:
            user = auth.create_user(email=email, password=password, display_name=fullname)
            print(f"User created successfully: {user.uid}")

            auth.set_custom_user_claims(user.uid, {"role": selected_role})
            print(f"Custom role '{selected_role}' set for user {user.uid}")

            # Optionally, create a basic profile in Firestore
            if db:
                profile_data = {
                    "uid": user.uid,
                    "name": fullname,
                    "email": email,
                    "role": selected_role,
                    "createdAt": datetime.utcnow().isoformat()
                }
                collection_name = f"{selected_role}s" # e.g., 'learners' or 'mentors'
                db.collection(collection_name).document(user.uid).set(profile_data)
                print(f"Basic profile created in Firestore '{collection_name}' collection for user {user.uid}")

            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('signin'))

        except auth.EmailAlreadyExistsError:
            flash("This email address is already registered.", "danger")
        except Exception as e:
            flash(f"An error occurred during signup: {str(e)}", "danger")
            print(f"Signup Error: {e}") # Log detailed error server-side

        return redirect(url_for('signup')) # Redirect back to signup on error

    return render_template('signup.html') # Assumes signup.html exists

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    """Handles user login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '') # No need for password check here, Firebase handles it on client

        if not email: # Basic check, client-side should handle more
             flash("Email is required.", "danger")
             return redirect(url_for('signin'))

        flash("Please use the Firebase login on the page.", "info")
        return redirect(url_for('signin'))


    return render_template('signin.html') # Assumes signin.html exists

@app.route('/sessionLogin', methods=['POST'])
def session_login():
    """Sets server-side session after successful Firebase client-side login."""
    data = request.get_json()
    id_token = data.get('idToken')

    if not id_token:
        return jsonify({"error": "ID token is missing."}), 400

    try:
        # Verify the ID token while checking for revocation.
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        uid = decoded_token['uid']
        user = auth.get_user(uid) # Get user details

        # Extract role from custom claims
        claims = decoded_token.get("custom_claims") or user.custom_claims or {} # Check token first, then user record
        role = claims.get("role", "user") # Default to 'user' if no role claim

        # Set session variables
        session['user_id'] = uid
        session['user_role'] = role
        session['email'] = user.email
        session['name'] = user.display_name or user.email # Use display name or email

        print(f"Session set for user: {uid}, role: {role}")

        return jsonify({"message": "Session set successfully", "role": role}), 200

    except auth.RevokedIdTokenError:
         return jsonify({"error": "Token revoked, please sign in again."}), 401
    except auth.UserDisabledError:
         return jsonify({"error": "User account is disabled."}), 401
    except auth.InvalidIdTokenError as e:
         print(f"Invalid ID Token: {e}")
         return jsonify({"error": "Invalid ID token."}), 401
    except Exception as e:
        print(f"Session Login Error: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/setCustomClaims', methods=['POST'])
def set_custom_claims():
    """Sets custom claims (role) for a user after signup."""
    data = request.get_json()
    id_token = data.get('idToken')
    role = data.get('role')

    if not id_token or not role:
        return jsonify({"error": "Missing ID token or role"}), 400

    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Set custom claims
        auth.set_custom_user_claims(uid, {"role": role})
        print(f"Custom claims set: UID={uid}, role={role}")

        return jsonify({"message": "Custom claims set successfully."}), 200

    except Exception as e:
        print(f"Error setting custom claims: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Clears the server-side session."""
    # Client-side should also call Firebase signOut()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route('/mentor_dashboard')
def mentor_dashboard():
    # Check if user is authenticated
    if 'user_id' not in session:
        flash('Please log in to access the mentor dashboard')
        return redirect(url_for('signin'))
    
    # Get user info from session
    user_id = session.get('user_id')
    
    # Render the mentor dashboard template
    return render_template('mentor_dashboard.html')

@app.route('/get_mentor_profile')
def get_mentor_profile():
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    if session.get('user_role') != 'mentor':
         return jsonify({'error': 'Access denied: Not a mentor'}), 403

    user_id = session['user_id']
    if not db: return jsonify({'error': 'Database service unavailable'}), 503
    
    user_id = session.get('user_id')
    
    # Query the mentor profile from Firestore
    try:
        mentor_ref = db.collection('mentors').document(user_id)
        mentor_doc = mentor_ref.get()
        
        if mentor_doc.exists:
            return jsonify(mentor_doc.to_dict())
        else:
            # Return empty profile with user ID if it doesn't exist yet
            return jsonify({'uid': user_id, 'email': session.get('user_email', '')})
    
    except Exception as e:
        print(f"Error fetching mentor profile: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/update_mentor_profile', methods=['POST'])
@role_required('mentor')
def update_mentor_profile():
    """Updates mentor profile in Firestore."""
    if not db: return jsonify({"error": "Database not available"}), 500
    uid = session.get('user_id')
    
    try:
        data = request.get_json()
        required_fields = ["name", "email"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        mentor_data = {
            "uid": uid,
            "name": data.get("name"),
            "email": data.get("email"),
            "age": data.get("age"),
            "gender": data.get("gender"),
            "primaryskill": data.get("primaryskill"),
            "availableDay": data.get("availableDay"),
            "availableTime": data.get("availableTime"),
            "experience": data.get("experience"),
            "bio": data.get("bio"),
            "updatedAt": datetime.utcnow().isoformat()
        }
        
        # Update in Firestore
        db.collection("mentors").document(uid).set(mentor_data, merge=True)
        
        # Check for learners that match this mentor's skill and time
        #find_and_link_learners_by_mentor_profile(mentor_data)
        check_and_notify_matching_learners(mentor_data)
        
        return jsonify({"success": True, "message": "Profile updated successfully"}), 200
        
    except Exception as e:
        print(f"Error updating mentor profile: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/learner_dashboard')
@role_required('learner') # Use decorator to check role
def learner_dashboard():
    """Renders the learner dashboard."""
    return render_template('learner_dashboard.html') # Assumes learner_dashboard.html exists

@app.route('/create_learner_profile', methods=['POST'])
@role_required('learner')
def create_learner_profile():
    """Creates or updates learner profile data in Firestore."""
    if not db:
        return jsonify({"error": "Database not available"}), 500

    data = request.get_json()
    uid = session.get('user_id')  # Get UID from session

    # Required fields from the learner form
    required_fields = ["name", "email", "age", "gender", "skillinterest", "skilllevel", "preferreddays", "preferredtime"]
    missing_fields = [field for field in required_fields if not data.get(field)]

    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        learner_data = {
            "uid": uid,
            "name": data.get("name"),
            "email": data.get("email"),
            "age": data.get("age"),
            "gender": data.get("gender"),
            "skillinterest": data.get("skillinterest"),
            "skilllevel": data.get("skilllevel"),
            "preferreddays": data.get("preferreddays"),  # e.g., "Weekends"
            "preferredtime": data.get("preferredtime"),  # e.g., "Evening (4:30PM - 6PM)"
            "learning_goal": data.get("learning_goal", ""),
            "updatedAt": datetime.utcnow().isoformat()
        }

        db.collection("learners").document(uid).set(learner_data, merge=True)
        return jsonify({"status": "success", "message": "Learner profile saved.", "data": learner_data}), 200

    except Exception as e:
        print(f"Error saving learner profile for {uid}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_learner_profile')
@role_required('learner')
def get_learner_profile():
    """Gets the current learner's profile data."""
    if not db: return jsonify({"error": "Database not available"}), 500
    uid = session.get('user_id')
    try:
        learner_doc = db.collection("learners").document(uid).get()
        if learner_doc.exists:
            return jsonify(learner_doc.to_dict())
        else:
            # Return basic info if profile doesn't exist yet
            return jsonify({"email": session.get('email'), "uid": uid, "message": "Profile not completed"})
    except Exception as e:
        print(f"Error getting learner profile for {uid}: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/update_learner_profile', methods=['POST'])
@role_required('learner')
def update_learner_profile():
    """Updates learner profile in Firestore."""
    if not db: return jsonify({"error": "Database not available"}), 500
    uid = session.get('user_id')
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["name", "email", "skillinterest", "skilllevel", "preferreddays", "preferredtime"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        learner_data = {
            "uid": uid,
            "name": data.get("name"),
            "email": data.get("email"),
            "age": data.get("age"),
            "gender": data.get("gender"),
            "skillinterest": data.get("skillinterest"),
            "skilllevel": data.get("skilllevel"),
            "preferreddays": data.get("preferreddays"),
            "preferredtime": data.get("preferredtime"),
            "goals": data.get("goals", ""),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update in Firestore
        db.collection("learners").document(uid).set(learner_data, merge=True)
        
        # Optional: Trigger a check for existing courses/mentors that match the *updated* profile
        #find_matching_courses_for_learner(learner_data)
        return jsonify({"success": True, "message": "Profile updated successfully"}), 200
        
    except Exception as e:
        print(f"Error updating learner profile: {e}")
        return jsonify({"error": str(e)}), 500
    
def send_match_notification_emails(learner_email, learner_name, mentor_email, mentor_name, course_name, teaching_slot):
    """
    Send email notifications to both learner and mentor about their match.
    
    In production, replace this with an actual email sending service like SendGrid, Mailgun, etc.
    """
    # For demonstration, print the email details
    print("-" * 50)
    print("SENDING MATCH NOTIFICATION EMAILS")
    print("-" * 50)
    
    # Email to learner
    print(f"To: {learner_email}")
    print(f"Subject: You've been matched with a mentor!")
    print(f"Body: Dear {learner_name},\n\n"
          f"We're excited to inform you that you've been matched with {mentor_name} "
          f"as your mentor for the course '{course_name}'.\n"
          f"Your sessions are scheduled for {teaching_slot}.\n\n"
          f"Please prepare for your first session and feel free to contact your mentor "
          f"with any questions.\n\n"
          f"Best regards,\nCraftEcho Team")
    
    print("-" * 25)
    
    # Email to mentor
    print(f"To: {mentor_email}")
    print(f"Subject: New Learner Assignment")
    print(f"Body: Dear {mentor_name},\n\n"
          f"A new learner, {learner_name}, has been assigned to you for "
          f"the course '{course_name}'.\n"
          f"Sessions are scheduled for {teaching_slot}.\n\n"
          f"Please review their profile and prepare for your first session.\n\n"
          f"Best regards,\nCraftEcho Team")
    
    print("-" * 50)
# --- Other API routes from original file (Keep if needed elsewhere, comment if only for old dashboard) ---

def check_and_notify_matching_learners(mentor_data):
    """Check for learners with matching skill and time preferences."""
    try:
        # Query for learners with matching skill, day and time
        learners_ref = db.collection('learners')
        matching_learners = learners_ref.where('skillinterest', '==', mentor_data.get('primaryskill')) \
                                       .where('preferreddays', '==', mentor_data.get('availableDay')) \
                                       .where('preferredtime', '==', mentor_data.get('availableTime')) \
                                       .stream()
        
        # For each matching learner, notify both learner and mentor
        for learner_doc in matching_learners:
            learner_data = learner_doc.to_dict()
            teaching_slot = f"{mentor_data.get('availableDay')} {mentor_data.get('availableTime')}"
            # Get or create a course for the skill
            courses_ref = db.collection('courses').where('skillinterest', '==', mentor_data.get('primaryskill')).limit(1).stream()
            courses = list(courses_ref)
            
            if courses:
                course_data = courses[0].to_dict()
                course_name = course_data.get('name')
            else:
                course_name = f"{mentor_data.get('primaryskill')} Fundamentals"
            
            # Send notifications
            send_match_notification_emails(
                learner_email=learner_data.get('email'),
                learner_name=learner_data.get('name'),
                mentor_email=mentor_data.get('email'),
                mentor_name=mentor_data.get('name'),
                course_name=course_name,
                teaching_slot=teaching_slot
            )
    except Exception as e:
        print(f"Error checking for matching learners: {e}")

@app.route('/create_mentor_profile', methods=['POST'])
@role_required('mentor')
def create_mentor_profile():
    """Creates or updates mentor profile data in Firestore."""
    if not db: return jsonify({"error": "Database not available"}), 500
    data = request.get_json()
    uid = session.get('user_id') # Get UID from session

    # Basic validation
    required_fields = ["name", "email"] # Example required fields
    if not all(data.get(field) for field in required_fields):
        return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400

    try:
        mentor_data = {
            "uid": uid,
            "name": data.get("name"),
            "email": data.get("email"), # Should match auth email ideally
            "age": data.get("age"),
            "gender": data.get("gender"),
            "experience": data.get("experience"),
            "bio": data.get("bio"),
            "primaryskill": data.get("primaryskill"), # Important for matching
            "availableDay": data.get("availableDay"),
            "availableTime": data.get("availableTime"),
            "updatedAt": datetime.utcnow().isoformat()
            # Add other fields as needed (e.g., rating, hourlyRate)
        }
        db.collection("mentors").document(uid).set(mentor_data, merge=True) # Use merge=True to update existing
        return jsonify({"status": "success", "message": "Mentor profile saved.", "data": mentor_data}), 200
    except Exception as e:
        print(f"Error saving mentor profile for {uid}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/get_courses_by_mentor_email/<mentor_email>', methods=['GET'])
def get_courses_by_mentor_email(mentor_email):
    """Returns all courses created by the mentor with given email."""
    if not db:
        return jsonify({"error": "Database not available", "courses": []}), 500
    try:
        import urllib.parse
        decoded_email = urllib.parse.unquote(mentor_email)
        courses_ref = db.collection('courses').where("mentor_email", "==", decoded_email).stream()
        courses = []
        for doc in courses_ref:
             course_data = doc.to_dict()
             course_data['id'] = doc.id
             courses.append(course_data)
        return jsonify({"courses": courses}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_assignment_email_placeholder(learner_email, learner_name, mentor_email, mentor_name, course_name):
    """Placeholder function to simulate sending emails. Replace with real implementation."""
    print("-" * 20)
    print("--- SIMULATING EMAIL SEND ---")
    print(f"To Learner: {learner_email}")
    print(f"Subject: Mentor Assignment & Course Recommendation")
    print(f"Body: Hi {learner_name}, you've been assigned mentor {mentor_name} for the course '{course_name}'.")
    print("-" * 10)
    print(f"To Mentor: {mentor_email}")
    print(f"Subject: New Learner Assignment")
    print(f"Body: Hi {mentor_name}, you have been assigned learner {learner_name} interested in '{course_name}'.")
    print("-" * 20)
    # In a real app: Use Flask-Mail, SendGrid API, etc. here
    # mail = Mail(app) # Example
    # msg_learner = Message(...)
    # msg_mentor = Message(...)
    # mail.send(msg_learner)
    # mail.send(msg_mentor)

@app.route('/process_video', methods=['POST'])
def process_video():
    """
    Handles POST request to process a single YouTube video link.
    Calls the video_content script and returns processed data.
    """
    HF_API_TOKEN = "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"
    if not HF_API_TOKEN:
         return jsonify({"error": "Video processing service not configured (missing API key)."}), 500

    data = request.get_json()
    youtube_link = data.get('youtube_link')

    if not youtube_link:
        return jsonify({"error": "Missing 'youtube_link' in request."}), 400

    logging.info(f"Received request to process video: {youtube_link}")

    try:
        # Call the processing function from video_content.py
        # Pass the API token securely (video_content should ideally get it from env)
        # If video_content doesn't get from env, pass it: process_youtube_video(youtube_link, HF_API_TOKEN)
        results = video_content.process_youtube_video(youtube_link, HF_API_TOKEN) # Assuming video_content uses env var internally now

        if results.get("error"):
            logging.error(f"Error processing video {youtube_link}: {results['error']}")
            # Return a more user-friendly error if possible
            error_message = f"Failed to process video: {results['error']}"
            if "API" in error_message or "token" in error_message.lower():
                 error_message = "Video processing failed due to an external service issue. Please try again later."
            elif "download" in error_message.lower():
                 error_message = "Could not download video audio. Check the link or try again later."
            elif "format" in error_message.lower():
                  error_message = "Video format might be incompatible or processing failed."

            return jsonify({"error": error_message}), 500 # Internal Server Error

        # Return successful results
        logging.info(f"Successfully processed video: {youtube_link}")
        return jsonify({
            "message": "Video processed successfully!",
            "transcription": results.get("transcription"),
            "summary": results.get("summary"),
            "learning_content": results.get("learning_content")
        }), 200

    except Exception as e:
        logging.error(f"Unexpected error in /process_video for {youtube_link}: {e}", exc_info=True)
        return jsonify({"error": f"An internal server error occurred during video processing."}), 500

@app.route('/add_courses', methods=['POST'])
@role_required('mentor')
def add_courses():
    """
    Accepts one or more course entries from a mentor, saves them,
    and triggers matching logic.
    """
    if not db:
        return jsonify({"error": "Database service not available."}), 503

    mentor_id = session.get('user_id')
    if not mentor_id:
        return jsonify({"error": "Authentication error."}), 401

    try:
        data = request.get_json()
        courses_data = data.get('courses') # Expecting a list

        if not isinstance(courses_data, list):
             # Handle single object submission if necessary
             if isinstance(courses_data, dict):
                 courses_data = [courses_data]
             else:
                 return jsonify({"error": "Invalid data format: 'courses' should be a list."}), 400

        # --- Fetch mentor profile data ONCE ---
        mentor_profile = None
        try:
            mentor_doc = db.collection('mentors').document(mentor_id).get()
            if mentor_doc.exists:
                mentor_profile = mentor_doc.to_dict()
                mentor_profile['uid'] = mentor_id # Ensure UID is in the dict
            else:
                logging.warning(f"Mentor profile not found for UID {mentor_id} when adding course. Matching will be skipped.")
        except Exception as profile_e:
             logging.error(f"Failed to fetch mentor profile {mentor_id} for matching: {profile_e}", exc_info=True)
        # --- End fetch mentor profile ---


        added_refs = [] # Store references to added courses
        errors = []

        for course_entry in courses_data:
            if not isinstance(course_entry, dict):
                 errors.append("Invalid course entry found in list.")
                 continue

            # Basic validation
            required = ['title', 'mentor_email', 'youtube_link'] # Add others like 'summary' if now required
            missing = [f for f in required if not course_entry.get(f)]
            if missing:
                errors.append(f"Course '{course_entry.get('title', 'N/A')}' missing fields: {', '.join(missing)}")
                continue

            # Prepare course data for Firestore
            course_to_save = {
                "title": course_entry.get("title"),
                "mentor_email": course_entry.get("mentor_email"), # Validate against session email?
                "youtube_link": course_entry.get("youtube_link"),
                "additional_info": course_entry.get("additional_info", ""),
                # Include processed content (summary, transcript, learning_content)
                "summary": course_entry.get("summary", "[Not Provided]"),
                "transcript": course_entry.get("transcript", "[Not Provided]"),
                "learning_content": course_entry.get("learning_content", "[Not Provided]"),
                # Add mentor ID and timestamp
                "mentor_id": mentor_id,
                "created_at": firestore.SERVER_TIMESTAMP
            }

            # Optional: Add tags based on mentor skill
            if mentor_profile and mentor_profile.get('primaryskill'):
                course_to_save['tags'] = firestore.ArrayUnion([mentor_profile['primaryskill']])

            try:
                # Add course to Firestore
                update_time, course_ref = db.collection('courses').add(course_to_save)
                added_refs.append(course_ref)
                logging.info(f"Added course '{course_to_save['title']}' (ID: {course_ref.id}) for Mentor {mentor_id}")
            except Exception as e:
                logging.error(f"Error adding course '{course_entry.get('title')}' to Firestore: {e}", exc_info=True)
                errors.append(f"Failed to save course: {course_entry.get('title', 'N/A')}")

        # --- Trigger matching for EACH added course AFTER loop ---
        if mentor_profile: # Only match if mentor profile was found
            for course_ref in added_refs:
                 find_and_link_learners(course_ref, mentor_profile)
        # --- End Trigger Matching ---

        # Prepare response
        response_message = f"Processed {len(courses_data)} course entries. Successfully added: {len(added_refs)}."
        status_code = 200
        if errors:
            response_message += f" Errors occurred for {len(errors)} entries."
            status_code = 207 # Multi-Status

        return jsonify({"message": response_message, "errors": errors}), status_code

    except Exception as e:
        logging.error(f"Unexpected error in /add_courses for mentor {mentor_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500


@app.route('/get_courses', methods=['GET'])
def get_courses():
    if not db:
        return jsonify({"error": "Database not available", "courses": []}), 503

    try:
        courses_ref = db.collection('courses').order_by('created_at', direction=firestore.Query.DESCENDING)
        docs = courses_ref.stream()

        courses = []
        for doc in docs:
            course_data = doc.to_dict()
            course_data['id'] = doc.id  # Include Firestore document ID

            # Format created_at timestamp to ISO string if possible
            if 'created_at' in course_data and hasattr(course_data['created_at'], 'isoformat'):
                course_data['created_at_iso'] = course_data['created_at'].isoformat()

            courses.append(course_data)

        logging.info(f"Retrieved {len(courses)} courses from Firestore.")
        return jsonify({"courses": courses}), 200

    except Exception as e:
        logging.error(f"Error retrieving courses from Firestore: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to retrieve courses.",
            "courses": []
        }), 500

# --- NEW Route for Mentor's Own Courses ---
@app.route('/get_my_courses', methods=['GET'])
@role_required('mentor')
def get_my_courses():
    """Retrieves all courses submitted by the currently logged-in mentor."""
    if not db: return jsonify({"error": "Database service unavailable", "courses": []}), 503
    mentor_id = session.get('user_id')

    try:
        courses_ref = db.collection('courses')
        query = courses_ref.where('mentor_id', '==', mentor_id) \
                           .order_by('created_at', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        courses = []
        for doc in docs:
            course_data = doc.to_dict()
            course_data['id'] = doc.id
            # Convert timestamp if needed for display
            if 'created_at' in course_data and hasattr(course_data['created_at'], 'isoformat'):
                 course_data['created_at_iso'] = course_data['created_at'].isoformat()
            courses.append(course_data)

        logging.info(f"Retrieved {len(courses)} courses for Mentor {mentor_id}")
        return jsonify({"courses": courses}), 200

    except Exception as e:
        logging.error(f"Error retrieving courses for Mentor {mentor_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve your courses.", "courses": []}), 500

@app.route('/get_matched_courses', methods=['GET'])
@role_required('learner')
def get_matched_courses():
    """Retrieves courses matched to the logged-in learner based on skill/time."""
    if not db: return jsonify({"error": "Database service unavailable", "courses": []}), 503
    learner_id = session.get('user_id')

    try:
        learner_doc = db.collection('learners').document(learner_id).get()
        if not learner_doc.exists:
            return jsonify({"error": "Learner profile not found.", "courses": []}), 404

        learner_data = learner_doc.to_dict()
        matched_ids = learner_data.get('matched_course_ids', [])

        if not matched_ids:
            logging.info(f"No matched course IDs found for Learner {learner_id}")
            return jsonify({"courses": []}), 200 # Return empty list, not an error

        # Fetch details for each matched course ID
        # Note: Firestore doesn't have a direct "IN" query for many IDs efficiently without workarounds.
        # Fetching one by one is simpler for moderate numbers but can be slow for many matches.
        # Consider alternative data structures or batch gets if performance becomes an issue.
        matched_courses = []
        courses_ref = db.collection('courses')
        for course_id in matched_ids:
             try:
                course_doc = courses_ref.document(course_id).get()
                if course_doc.exists:
                    course_data = course_doc.to_dict()
                    course_data['id'] = course_doc.id
                    # Convert timestamp if needed
                    if 'created_at' in course_data and hasattr(course_data['created_at'], 'isoformat'):
                        course_data['created_at_iso'] = course_data['created_at'].isoformat()
                    matched_courses.append(course_data)
                else:
                    logging.warning(f"Matched Course ID {course_id} not found in courses collection for Learner {learner_id}")
             except Exception as fetch_e:
                  logging.error(f"Error fetching details for matched course {course_id} for Learner {learner_id}: {fetch_e}")

        # Optional: Sort matched courses by date?
        matched_courses.sort(key=lambda x: x.get('created_at_iso', ''), reverse=True)


        logging.info(f"Retrieved {len(matched_courses)} matched courses for Learner {learner_id}")
        return jsonify({"courses": matched_courses}), 200

    except Exception as e:
        logging.error(f"Error retrieving matched courses for Learner {learner_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve matched courses.", "courses": []}), 500

@app.route('/get_courses_by_skill/<skill>', methods=['GET'])
def get_courses_by_skill(skill):
    """Retrieves courses filtered by skill."""
    if not db: return jsonify({"error": "Database not available"}), 500
    try:
        courses_ref = db.collection('courses').where("skill", "==", skill).stream()
        courses = []
        for doc in courses_ref:
            course_data = doc.to_dict()
            course_data['id'] = doc.id
            courses.append(course_data)
        return jsonify({"courses": courses}), 200
    except Exception as e:
        print(f"Error getting courses by skill {skill}: {e}")
        return jsonify({"error": str(e)}), 500


# --- Debug Route (Remove in Production) ---
@app.route("/debug_session")
def debug_session():
    """Debug route to check session contents (REMOVE IN PRODUCTION)."""
    if os.environ.get('FLASK_DEBUG', 'False').lower() != 'true':
         return "Debug route disabled.", 403 # Disable if not in debug mode
    return jsonify(dict(session))

# --- Main Execution ---
if __name__ == "__main__":
    # Use environment variables for host, port, and debug for flexibility
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host=host, port=port, debug=debug_mode)