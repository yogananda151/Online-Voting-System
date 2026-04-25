import os # Import the operating system module for file path operations.
import pandas as pd # Import pandas for reading and manipulating Excel files (for voter uploads).
from datetime import datetime # Import datetime for handling election start and end times.

import MySQLdb # Import the MySQL database connector library.
# Import necessary components from the Flask framework:
from flask import Flask, render_template, request, redirect, url_for, session, flash
# Import security utilities for hashing and checking passwords:
from werkzeug.security import generate_password_hash, check_password_hash
# Import utility for securely handling uploaded filenames:
from werkzeug.utils import secure_filename
from config import Config # Import the custom configuration class.
import cv2 # Import OpenCV (cv2) for computer vision tasks (face recognition).
import numpy as np # Import numpy for mathematical operations, especially array handling (HOG features).


app = Flask(__name__) # Initialize the Flask application instance.
app.config.from_object(Config) # Load configuration settings from the Config object.
Config.init_app(app) # Initialize app-specific configuration (if Config class requires it).

# Database connection
def get_db(): # Define a function to create and return a database connection.
    """Establishes and returns a connection to the MySQL database.""" # Docstring explaining the function's purpose.
    return MySQLdb.connect( # Return the connection object using parameters from app.config.
        host=app.config['MYSQL_HOST'], # Database server host address.
        user=app.config['MYSQL_USER'], # Database user name.
        password=app.config['MYSQL_PASSWORD'], # Database password.
        db=app.config['MYSQL_DB'] # Database name.
    )

# Allowed file extensions
def allowed_file(filename): # Define a function to check if a file extension is permitted.
    """Checks if a filename has an allowed extension (for uploads).""" # Docstring for the file checker.
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'] # Check for dot and if the extension is in the allowed list.

# Home route
@app.route('/') # Decorator defines the default root URL route.
def home(): # Define the function to handle requests to the root URL.
    """Default entry point, redirects to the voter login page.""" # Docstring.
    return redirect(url_for('voter_login')) # Immediately redirect the user to the voter login page.

# --------------------- Voter Routes (Authentication & Voting) ---------------------

def capture_and_verify_face(): # Defines a simple, older function for basic face presence check.
    """
    DEPRECATED/SIMPLE face capture utility using basic Haar Cascade.
    Opens webcam, detects face, and waits for SPACE key press to verify presence.
    The main login/register uses HOG features (get_face_features, compare_faces).
    """ # Docstring detailing the function and its limited use.
    # Load the pre-trained Haar Cascade classifier for frontal face detection:
    face_cascade = cv2.CascadeClassifier(cv2.data.haascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0) # Open the default webcam (index 0).
    
    while True: # Start an infinite loop to read frames from the camera.
        ret, frame = cap.read() # Read a frame (ret is True/False, frame is the image data).
        if not ret: # Check if reading the frame failed.
            cap.release() # Release the camera resources.
            return False # Return False indicating capture failure.
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Convert the captured frame to grayscale (improves detection speed).
        faces = face_cascade.detectMultiScale(gray, 1.3, 5) # Detect faces in the grayscale image.
        
        for (x, y, w, h) in faces: # Loop through all detected faces.
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2) # Draw a green rectangle around the detected face.
            
        cv2.imshow('Face Verification - Look at camera (Press SPACE to verify, Q to quit)', frame) # Display the frame in a window.
        
        key = cv2.waitKey(1) & 0xFF # Wait 1ms for a key press.
        if key == ord('q'): # If the 'q' key is pressed, quit the loop.
            break
        elif key == ord(' ') and len(faces) > 0: # If SPACE is pressed AND a face is detected:
            cap.release() # Release the camera.
            cv2.destroyAllWindows() # Close the display windows.
            return True # Return True indicating successful verification.
    
    cap.release() # Release camera if loop breaks via 'q'.
    cv2.destroyAllWindows() # Close windows if loop breaks via 'q'.
    return False # Return False if the verification was not successful.


def get_face_features(frame, face_cascade): # Define function to extract HOG features from a face.
    """
    Extracts face features using the Histogram of Oriented Gradients (HOG) descriptor.
    HOG features are stored for biometric verification.
    """ # Docstring detailing HOG feature extraction.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Convert the input frame to grayscale.
    faces = face_cascade.detectMultiScale(gray, 1.3, 5) # Detect faces using the Haar Cascade.
    
    if len(faces) == 0: # Check if no face was detected in the frame.
        return None # Return None if no face is found.
        
    (x, y, w, h) = faces[0] # Get the coordinates of the first detected face.
    face = gray[y:y+h, x:x+w] # Crop the face region from the grayscale image.
    face = cv2.resize(face, (128, 128)) # Resize the face image to a standard size (128x128).
    
    # Calculate HOG features
    hog = cv2.HOGDescriptor() # Initialize the HOG descriptor object.
    features = hog.compute(face) # Compute the HOG features vector for the resized face.
    return features # Return the calculated HOG features vector (numpy array).

def compare_faces(stored_features, current_features, threshold=0.80 ): # Define function to compare two feature sets using cosine similarity.
    """
    Compares two sets of face features (HOG arrays) using cosine similarity.
    Returns True if similarity exceeds the threshold (biometric match).
    """ # Docstring detailing the comparison method.
    if stored_features is None or current_features is None: # Check if either feature set is missing.
        return False # Return False if comparison is impossible.
    
    # Convert features from database bytes back into a numpy array (float32 is assumed)
    if isinstance(stored_features, bytes): # Check if the stored features are in raw byte format (from MySQL BLOB).
        stored_features = np.frombuffer(stored_features, dtype=np.float32) # Convert bytes back to a numpy array of float32.
    
    # Calculate cosine similarity: (A dot B) / (|A| * |B|)
    # Calculate the dot product, divided by the product of their L2 norms (magnitudes).
    similarity = np.dot(stored_features.flatten(), current_features.flatten()) / \
                (np.linalg.norm(stored_features) * np.linalg.norm(current_features))
    
    return similarity > threshold # Return True if the calculated similarity is greater than the required threshold (0.80).

@app.route('/voter/register', methods=['GET', 'POST']) # Define the route for registration, accepting GET (show form) and POST (submit form).
def voter_register(): # Define the view function for voter registration.
    """Handles voter registration with password hashing and face feature capture.""" # Docstring.
    if request.method == 'POST': # Check if the user is submitting the form data.
        # 1. Get and hash form data
        full_name = request.form['full_name'] # Retrieve the full name from the form.
        voter_id = request.form['voter_id'] # Retrieve the unique voter ID.
        email = request.form['email'] # Retrieve the email address.
        password = generate_password_hash(request.form['password']) # Hash the password for secure storage.
        
        # 2. Initialize face capture
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') # Load face detector.
        cap = cv2.VideoCapture(0) # Open the default webcam.
        face_features = None # Initialize variable to store HOG features.
        
        # 3. Capture face features via webcam
        while True: # Start the webcam capture loop.
            ret, frame = cap.read() # Read a frame from the camera.
            if not ret: # Check for camera read failure.
                flash('Camera error!', 'danger') # Display an error message.
                return redirect(url_for('voter_register')) # Redirect back to the registration page.
            
            # Display webcam view with detected face rectangle
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Convert frame to grayscale.
            faces = face_cascade.detectMultiScale(gray, 1.3, 5) # Detect faces in the frame.
            for (x, y, w, h) in faces: # Iterate through detected faces.
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2) # Draw a green box around the face.
            
            cv2.imshow('Look directly at camera (Press SPACE when ready)', frame) # Show the live video feed.
            
            key = cv2.waitKey(1) & 0xFF # Check for key press.
            if key == ord('q'): # If 'q' is pressed, break the capture loop.
                break
            elif key == ord(' ') and len(faces) > 0: # If SPACE is pressed AND a face is visible:
                # Extract features when SPACE is pressed and a face is visible
                face_features = get_face_features(frame, face_cascade) # Call helper function to extract HOG features.
                if face_features is not None: # If feature extraction was successful:
                    break # Exit the capture loop.
        
        cap.release() # Release the camera resource.
        cv2.destroyAllWindows() # Close the OpenCV display windows.
        
        if face_features is None: # Check if face features were successfully captured and extracted.
            flash('Face registration failed. Please try again.', 'danger') # Flash failure message.
            return redirect(url_for('voter_register')) # Redirect for another attempt.
        
        # 4. Save data to database
        conn = get_db() # Get a new database connection.
        cursor = conn.cursor() # Create a cursor object for executing queries.
        
        try: # Start a try block for database operations.
            # face_features is converted to raw bytes before saving to MySQL BLOB/LONGBLOB
            cursor.execute( # Execute the INSERT query.
                "INSERT INTO voters (full_name, voter_id, email, password, face_features) VALUES (%s, %s, %s, %s, %s)",
                (full_name, voter_id, email, password, face_features.tobytes()) # Pass the voter data and HOG features (as bytes).
            )
            conn.commit() # Commit the transaction to save the new voter record.
            flash('Registration successful!', 'success') # Display success message.
            return redirect(url_for('voter_login')) # Redirect to the login page.
        except Exception as e: # Catch any potential database or other exceptions.
            flash(f'Registration failed: {str(e)}', 'danger') # Display the specific error message.
        finally: # Ensure the connection is properly closed regardless of success/failure.
            cursor.close() # Close the cursor.
            conn.close() # Close the database connection.
    
    # GET request: render the registration form
    return render_template('voter/register.html') # Render the HTML template for the registration form.

@app.route('/voter/login', methods=['GET', 'POST']) # Define the route for login, accepting GET and POST.
def voter_login(): # Define the view function for voter login.
    """Handles voter login with password verification and mandatory face verification.""" # Docstring.
    if request.method == 'POST': # Check if the login form was submitted.
        identifier = request.form['identifier'] # Get the email or voter ID used for login.
        password = request.form['password'] # Get the raw password.
        
        conn = get_db() # Get a database connection.
        # Use DictCursor to access columns by name (e.g., voter['password']) for convenience:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor) 
        
        try: # Start a try block for login and verification logic.
            # 1. Check credentials (email or voter_id)
            cursor.execute( # Execute a query to find the voter by email OR voter ID.
                "SELECT * FROM voters WHERE email = %s OR voter_id = %s",
                (identifier, identifier) # Pass the identifier twice for the OR condition.
            )
            voter = cursor.fetchone() # Fetch the first matching voter record.
            
            # 2. Check hashed password
            if voter and check_password_hash(voter['password'], password): # Check if voter exists AND password matches the hash.
                # 3. Initialize face verification
                # NOTE: The provided code has 'haascades' typo, correcting to 'haarcascades' is necessary for it to run:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') # Load the face detector.
                cap = cv2.VideoCapture(0) # Open the webcam.
                verification_attempts = 0 # Initialize attempt counter.
                max_attempts = 3 # Set maximum allowed attempts.
                
                # Biometric verification loop (up to 3 attempts)
                while verification_attempts < max_attempts: # Loop until max attempts are reached.
                    ret, frame = cap.read() # Read a frame.
                    if not ret: # Check for camera error.
                        break # Exit the loop if camera fails.
                    
                    # Display webcam view
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Grayscale conversion.
                    faces = face_cascade.detectMultiScale(gray, 1.3, 5) # Detect faces.
                    for (x, y, w, h) in faces: # Draw rectangle around face.
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    cv2.imshow(f'Face Verification (Attempt {verification_attempts + 1}/{max_attempts})', frame) # Show live video with attempt count.
                    
                    key = cv2.waitKey(1) & 0xFF # Check for key press.
                    # Proceed with feature extraction/comparison on SPACE press
                    if key == ord(' ') and len(faces) > 0: # If SPACE pressed and face detected:
                        current_features = get_face_features(frame, face_cascade) # Extract HOG features from the live frame.
                        # 4. Compare live features with stored features
                        if current_features is not None and compare_faces(voter['face_features'], current_features): # Compare features for a match.
                            # Success: Close camera, set session, redirect
                            cap.release() # Release camera.
                            cv2.destroyAllWindows() # Close windows.
                            session['voter_id'] = voter['id'] # Store the voter's ID in the session to maintain login state.
                            flash('Login successful!', 'success') # Flash success message.
                            return redirect(url_for('voter_dashboard')) # Redirect to the dashboard.
                        verification_attempts += 1 # Increment attempt counter if face detection failed.
                    elif key == ord('q'): # If 'q' is pressed, exit verification.
                        break
                
                # If loop finishes without success
                cap.release() # Release camera if loop exited.
                cv2.destroyAllWindows() # Close windows if loop exited.
                flash('Face verification failed!', 'danger') # Flash biometric failure message.
            else:
                flash('Invalid credentials!', 'danger') # Flash password/credential failure message.
        finally: # Ensure resources are cleaned up.
            cursor.close() # Close the cursor.
            conn.close() # Close the database connection.
    
    # GET request: render the login form
    return render_template('voter/login.html') # Render the login form template.


# Voter Dashboard
@app.route('/voter/dashboard') # Define the dashboard route.
def voter_dashboard(): # Define the dashboard view function.
    """Displays the voter's main page after successful login.""" # Docstring.
    if 'voter_id' not in session: # Check if the voter is logged in.
        return redirect(url_for('voter_login')) # If not logged in, redirect to login.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    # Check voter's status (e.g., if they have voted globally)
    cursor.execute("SELECT has_voted FROM voters WHERE id = %s", (session['voter_id'],)) # Fetch voter's general voting status.
    voter = cursor.fetchone() # Get the result.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('voter/dashboard.html', voter=voter) # Render dashboard with voter info.


@app.route('/voter/elections') # Define the route to view elections.
def voter_elections(): # Define the view function.
    """Displays all elections that are currently active and open for voting.""" # Docstring.
    if 'voter_id' not in session: # Check if voter is logged in.
        return redirect(url_for('voter_login')) # Redirect if not logged in.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    now = datetime.now() # Get the current date and time.
    # Query for elections that are marked active AND are within the start/end time window
    cursor.execute("SELECT * FROM elections WHERE is_active = TRUE AND start_time <= %s AND end_time >= %s", (now, now)) # Select active and currently running elections.
    elections = cursor.fetchall() # Fetch all matching elections.
    cursor.close() # Close cursor.
    conn.close() # Close connection.

    if not elections: # Check if no elections were returned.
        flash('No active elections available at the moment.', 'info') # Display informational message.
    return render_template('voter/elections.html', elections=elections) # Render the elections list page.

# View Candidates
@app.route('/voter/candidates/<int:election_id>') # Define route to view candidates for a specific election ID.
def voter_candidates(election_id): # Define view function, taking election_id as an integer argument.
    """Displays the list of candidates for a specific active election.""" # Docstring.
    if 'voter_id' not in session: # Check login state.
        return redirect(url_for('voter_login')) # Redirect if not logged in.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # Check if the requested election is active and within the time frame
    now = datetime.now() # Get current time.
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE AND start_time <= %s AND end_time >= %s", (election_id, now, now)) # Check if the election is currently open.
    election = cursor.fetchone() # Fetch the election details.
    if not election: # If election is not found or not active/open:
        flash('This election is not active or not within the voting time!', 'warning') # Flash warning.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('voter_elections')) # Redirect back to the general elections list.

    # Get candidates for this valid election
    cursor.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,)) # Fetch all candidates for the validated election.
    candidates = cursor.fetchall() # Get all candidates.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('voter/candidates.html', candidates=candidates, election=election) # Render candidate list page.

@app.route('/voter/results/select') # Define route for results selection page.
def voter_results_select(): # Define view function.
    """Allows voters to select an election to view results for.""" # Docstring.
    if 'voter_id' not in session: # Check login state.
        return redirect(url_for('voter_login')) # Redirect if not logged in.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.

    # Check the global setting for result publishing
    cursor.execute("SELECT results_published FROM admin_settings WHERE id = 1") # Query the admin settings table.
    settings = cursor.fetchone() # Fetch the settings row.

    if settings and settings.get('results_published'): # If results are globally published by the admin:
        # If published globally, show all elections
        cursor.execute("SELECT * FROM elections ORDER BY end_time DESC") # Show all elections, regardless of status.
    else:
        # If not published globally, only show elections that have officially ended/been marked inactive
        cursor.execute("SELECT * FROM elections WHERE is_active = FALSE ORDER BY end_time DESC") # Show only completed/inactive elections.

    elections = cursor.fetchall() # Fetch the list of elections to display.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('voter/results_select.html', elections=elections) # Render the selection page.


# Cast Vote
@app.route('/vote/<int:candidate_id>', methods=['POST']) # Define the route for casting a vote (POST only), taking candidate ID.
def cast_vote(candidate_id): # Define the view function.
    """Handles the POST request to record a vote for a specific candidate.""" # Docstring.
    if 'voter_id' not in session: # Check if voter is logged in.
        return redirect(url_for('voter_login')) # Redirect if not.

    # Retrieve election_id from the submitted form data
    election_id = request.form.get('election_id') # Get the associated election ID from the form data.
    if not election_id: # Check if election ID is missing.
        flash('Election not specified!', 'danger') # Flash error.
        return redirect(url_for('voter_dashboard')) # Redirect to dashboard.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.

    # 1. Basic validation: Check if election is active and in time
    now = datetime.now() # Get current time.
    # Check if election is active and time bounds are met (handles NULL times too).
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE AND (start_time IS NULL OR start_time <= %s) AND (end_time IS NULL OR end_time >= %s)", (election_id, now, now))
    election = cursor.fetchone() # Fetch election details.
    if not election: # If the election is closed or inactive:
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        flash('This election is not active or not within the voting time!', 'warning') # Flash warning.
        return redirect(url_for('voter_dashboard')) # Redirect.

    # 2. Check if the voter is authorized (linked) to vote in this election
    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, session['voter_id'])) # Check the junction table for linkage.
    if not cursor.fetchone(): # If no linkage record is found:
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        flash('You are not registered for this election. You cannot vote.', 'danger') # Flash authorization error.
        return redirect(url_for('voter_dashboard')) # Redirect.

    # 3. Check for double voting (one vote per voter per election)
    cursor.execute( # Check the 'votes' table for an existing vote from this voter in this election.
        "SELECT * FROM votes WHERE voter_id = %s AND election_id = %s",
        (session['voter_id'], election_id)
    )
    already_voted = cursor.fetchone() # Fetch the result.
    if already_voted: # If a vote record exists:
        flash('You have already voted in this election!', 'danger') # Flash double vote error.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('voter_dashboard')) # Redirect.

    try: # Begin transaction attempt.
        # 4. Record vote in the 'votes' table
        cursor.execute( # Insert the new vote record.
            "INSERT INTO votes (voter_id, candidate_id, election_id) VALUES (%s, %s, %s)",
            (session['voter_id'], candidate_id, election_id)
        )
        # 5. Update global voter status (Optional, but present in schema)
        cursor.execute( # Update the voter's global voting flag.
            "UPDATE voters SET has_voted = 1 WHERE id = %s",
            (session['voter_id'],)
        )
        conn.commit() # Commit the changes to the database.
        flash('Vote cast successfully!', 'success') # Flash success.
    except Exception as e: # Catch any errors during the database write.
        conn.rollback() # Rollback the transaction to ensure data integrity.
        flash(f'Error: {str(e)}', 'danger') # Flash the error message.
    finally: # Clean up resources.
        cursor.close() # Close cursor.
        conn.close() # Close connection.

    # Redirect to view results for the election just voted in
    return redirect(url_for('voter_results', election_id=election_id)) # Send voter to the results page.


# View Results
@app.route('/voter/results/<int:election_id>') # Define the route to view results for a specific election.
def voter_results(election_id): # Define the view function.
    """Displays the vote counts and percentages for a specific election.""" # Docstring.
    if 'voter_id' not in session: # Check login state.
        return redirect(url_for('voter_login')) # Redirect if not logged in.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # 1. Load global publish flag
    cursor.execute("SELECT results_published FROM admin_settings WHERE id = 1") # Check global results visibility flag.
    settings = cursor.fetchone() # Fetch the setting.

    # 2. Load election details
    cursor.execute("SELECT * FROM elections WHERE id = %s", (election_id,)) # Fetch the requested election details.
    election = cursor.fetchone() # Get the election row.
    if not election: # If election ID is invalid:
        flash('Election not found!', 'warning') # Flash error.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('voter_results_select')) # Redirect to the selection page.

    # Determine if results are safe to view
    now = datetime.now() # Get current time.
    results_published = bool(settings and settings.get('results_published')) # Convert setting to boolean.
    # Check if election has explicitly ended or been marked inactive
    election_ended = (not election.get('is_active')) or (election.get('end_time') is not None and election.get('end_time') <= now) # Check if election is definitely over.

    # 3. Security check: Only allow viewing if published globally OR election has ended
    if not results_published and not election_ended: # If not published AND not ended:
        flash('Results are not published yet!', 'warning') # Flash warning.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('voter_dashboard')) # Redirect to dashboard.
    
    # 4. Query: Count votes per candidate for the election
    cursor.execute(""" # Execute complex SQL query to join candidates, votes, count votes, and group by candidate.
    SELECT c.id, c.candidate_name, c.party_name, c.photo_path, c.symbol_path, COUNT(v.id) AS vote_count
    FROM candidates c
    LEFT JOIN votes v ON c.id = v.candidate_id AND v.election_id = %s
    WHERE c.election_id = %s
    GROUP BY c.id
    """, (election_id, election_id))
    
    results = cursor.fetchall() # Fetch all results rows.
    
    # 5. Calculation: Calculate total votes and percentage for each candidate
    total_votes = sum(candidate['vote_count'] for candidate in results) if results else 0 # Calculate the total number of votes cast.
    for candidate in results: # Loop through each candidate result.
        # Calculate percentage, preventing division by zero.
        candidate['percentage'] = round((candidate['vote_count'] / total_votes) * 100, 2) if total_votes > 0 else 0 
    
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    
    return render_template('voter/results.html', results=results, total_votes=total_votes) # Render results page.
# --------------------- Admin Routes (Management) ---------------------

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST']) # Define the route for admin login.
def admin_login(): # Define the view function.
    """Handles admin login (Note: password is NOT hashed here).""" # Docstring.
    if request.method == 'POST': # Check if the login form was submitted.
        username = request.form['username'] # Get username.
        password = request.form['password'] # Get password.
        
        conn = get_db() # Get connection.
        cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,)) # Query admin table by username.
        admin = cursor.fetchone() # Fetch the admin record.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        
        # Check if user exists and password matches (plain text check)
        if admin and admin['password'] == password: # Check if record found AND password matches the plain text stored password.
            session['admin_id'] = admin['id'] # Store admin ID in session to log them in.
            return redirect(url_for('admin_dashboard')) # Redirect to the admin dashboard.
        else:
            flash('Invalid credentials!', 'danger') # Flash authentication failure.
    
    return render_template('admin/login.html') # Render the admin login form (GET request).

# Admin Dashboard
@app.route('/admin/dashboard') # Define the admin dashboard route.
def admin_dashboard(): # Define the view function.
    """Shows key statistics for the system.""" # Docstring.
    if 'admin_id' not in session: # Check if admin is logged in.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor for count operations.
    # Get counts of all voters, candidates, and total votes cast
    cursor.execute("SELECT COUNT(*) FROM voters") # Count total voters.
    voters_count = cursor.fetchone()[0] # Fetch the count value.
    cursor.execute("SELECT COUNT(*) FROM candidates") # Count total candidates.
    candidates_count = cursor.fetchone()[0] # Fetch the count value.
    cursor.execute("SELECT COUNT(*) FROM votes") # Count total votes.
    votes_count = cursor.fetchone()[0] # Fetch the count value.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('admin/dashboard.html', # Render dashboard with statistics.
                          voters_count=voters_count,
                          candidates_count=candidates_count,
                          votes_count=votes_count)

# Add Election
@app.route('/admin/election/add', methods=['GET', 'POST']) # Define the route to add a new election.
def add_election(): # Define the view function.
    """Handles adding a new election and bulk uploading/linking voters via Excel.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not logged in.

    if request.method == 'POST': # Process form submission.
        election_name = request.form['name'] # Get election name.
        area = request.form['area'] # Get election area.
        start_time = request.form['start_time'] # Get start time string.
        end_time = request.form['end_time'] # Get end time string.

        conn = get_db() # Get connection.
        cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
        
        # 1. Insert the new election record
        cursor.execute( # Insert election details, defaulting to active (TRUE).
            "INSERT INTO elections (name, area, start_time, end_time, is_active) VALUES (%s, %s, %s, %s, TRUE)",
            (election_name, area, start_time, end_time)
        )
        election_id = cursor.lastrowid # Retrieve the auto-generated ID of the new election.

        # 2. Handle voters list upload
        inserted = 0 # Counter for new voters inserted.
        linked = 0 # Counter for existing voters linked.
        errors = 0 # Counter for skipped/error rows.
        if 'voters_file' in request.files: # Check if a file was uploaded with the form.
            file = request.files['voters_file'] # Get the uploaded file object.
            if file and allowed_file(file.filename): # Check if file exists and has an allowed extension.
                df = pd.read_excel(file) # Read the Excel file into a pandas DataFrame.
                # Normalize column names (lowercase, replace spaces with underscores)
                df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns] # Clean up column headers for easier access.
                
                for index, row in df.iterrows(): # Iterate over each row in the DataFrame.
                    try: # Start loop try block to handle row errors.
                        # Extract data from the Excel row
                        full_name = str(row.get('full_name', '')).strip() # Get full_name, convert to string, remove whitespace.
                        voter_id = str(row.get('voter_id', '')).strip() # Get voter_id.
                        email = str(row.get('email', '')).strip() # Get email.
                        password = str(row.get('password', '')).strip() # Get raw password.
                        if not (full_name and voter_id and email and password): # Check if required fields are present.
                            errors += 1 # Increment error counter if data is incomplete.
                            continue # Skip to the next row.

                        # Check if voter already exists in the system
                        cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email)) # Check if voter exists by ID or email.
                        existing = cursor.fetchone() # Fetch the result.
                        
                        if existing: # If a voter record was found:
                            # Voter exists: Link the existing voter to the new election
                            vid = existing['id'] # Get the existing voter's database ID.
                            cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid)) # Check if already linked.
                            if not cursor.fetchone(): # If not already linked:
                                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid)) # Create the linkage.
                                linked += 1 # Increment linked counter.
                            else:
                                # Already linked to this election
                                errors += 1 # Increment error counter (skipped linkage).
                            continue # Move to the next Excel row.

                        # Voter does not exist: Create new voter and then link
                        cursor.execute( # Insert the new voter into the 'voters' table.
                            "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                            (full_name, voter_id, email, generate_password_hash(password)) # Hash password for new voter and save.
                        )
                        new_vid = cursor.lastrowid # Get the ID of the newly inserted voter.
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid)) # Link the new voter to the election.
                        inserted += 1 # Increment inserted counter.
                    except Exception: # Catch any other errors during processing of this row.
                        errors += 1 # Increment error counter.
                        continue # Skip to next row on error

        conn.commit() # Commit all accumulated database changes (election and all voter inserts/links).
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        flash(f'Election created. {inserted} new voters added, {linked} existing voters linked, {errors} skipped.', 'success') # Flash summary message.
        return redirect(url_for('admin_elections')) # Redirect to the elections list.

    # GET request: render the election creation form
    return render_template('admin/add_elections.html') # Render the form template.

@app.route('/admin/elections', methods=['GET', 'POST']) # Define the route to view all elections.
def admin_elections(): # Define the view function.
    """Displays a list of all elections.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not logged in.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    # Fetch all elections, ordered by latest first
    cursor.execute("SELECT * FROM elections ORDER BY id DESC") # Select all elections, most recent first.
    elections = cursor.fetchall() # Fetch all results.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('admin/elections.html', elections=elections) # Render the elections list template.

@app.route('/admin/election/complete/<int:election_id>', methods=['POST']) # Define route to complete an election (POST only).
def complete_election(election_id): # Define the view function.
    """Marks an election as inactive and creates a snapshot of linked voters in the archive table.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not logged in.

    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor.

    # 1. Mark election inactive
    cursor.execute("UPDATE elections SET is_active = FALSE WHERE id = %s", (election_id,)) # Set the election status to FALSE.

    # 2. Archive voters: Insert records of all voters linked to this election into archive_voters table
    cursor.execute(""" # Execute query to insert a snapshot of linked voters into the archive table.
        INSERT INTO archive_voters (full_name, voter_id, email, password, has_voted, registered_at, election_id)
        SELECT v.full_name, v.voter_id, v.email, v.password, v.has_voted, v.registered_at, ev.election_id
        FROM voters v
        JOIN election_voters ev ON ev.voter_id = v.id
        WHERE ev.election_id = %s
    """, (election_id,)) # Select voters currently linked via election_voters table.

    conn.commit() # Commit the update and archive insert.
    cursor.close() # Close cursor.
    conn.close() # Close connection.

    flash('Election completed and voters archived (snapshot). Voters remain in system for future elections.', 'success') # Flash success message.
    return redirect(url_for('admin_elections')) # Redirect to the elections list.

# Manage Candidates
@app.route('/admin/candidate/add/<int:election_id>', methods=['GET', 'POST']) # Define the route to add a candidate.
def add_candidate(election_id): # Define the view function.
    """Allows admin to add a new candidate to a specific election, including image uploads.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not logged in.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    # Get the current election info
    cursor.execute("SELECT id, name FROM elections WHERE id = %s", (election_id,)) # Fetch election details by ID.
    election = cursor.fetchone() # Get the election row.

    if request.method == 'POST': # Process form submission.
        candidate_name = request.form['candidate_name'] # Get candidate name.
        party_name = request.form['party_name'] # Get party name.
        photo = request.files['photo'] # Get the uploaded photo file object.
        symbol = request.files['symbol'] # Get the uploaded symbol file object.

        photo_path = None # Initialize photo path variable.
        symbol_path = None # Initialize symbol path variable.

        # 1. Save candidate photo file
        if photo and allowed_file(photo.filename): # Check if a photo was uploaded and is allowed.
            filename = secure_filename(photo.filename) # Clean the filename for security.
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) # Save the file to the upload directory.
            photo_path = filename # Store the clean filename for the database.

        # 2. Save candidate symbol file
        if symbol and allowed_file(symbol.filename): # Check if a symbol was uploaded and is allowed.
            filename = secure_filename(symbol.filename) # Clean the filename.
            symbol.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) # Save the file.
            symbol_path = filename # Store the clean filename for the database.

        # 3. Insert candidate data into the database
        cursor.execute( # Insert the new candidate record.
            "INSERT INTO candidates (candidate_name, party_name, photo_path, symbol_path, election_id) VALUES (%s, %s, %s, %s, %s)",
            (candidate_name, party_name, photo_path, symbol_path, election_id) # Pass all data, including file paths.
        )
        conn.commit() # Commit the new record.
        flash('Candidate added successfully!', 'success') # Flash success.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('admin_candidates', election_id=election_id)) # Redirect to the candidate list for this election.

    cursor.close() # Close cursor (for GET request only).
    conn.close() # Close connection (for GET request only).
    # GET request: render the candidate addition form
    return render_template('admin/add_candidates.html', election=election, election_id=election_id) # Render the form.

@app.route('/admin/candidates/<int:election_id>') # Define the route to view candidates for a specific election.
def admin_candidates(election_id): # Define the view function.
    """Displays all candidates for a specific election.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    # Fetch all candidates linked to this election ID
    cursor.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,)) # Select all candidates belonging to the election.
    candidates = cursor.fetchall() # Fetch all candidates.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('admin/candidates.html', candidates=candidates, election_id=election_id) # Render the candidate list page.

# Edit Candidate
@app.route('/admin/candidate/edit/<int:id>', methods=['GET', 'POST']) # Define the route to edit a candidate by ID.
def edit_candidate(id): # Define the view function.
    """Allows admin to edit an existing candidate's details and update images.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    if request.method == 'POST': # Process form submission.
        candidate_name = request.form['candidate_name'] # Get updated candidate name.
        party_name = request.form['party_name'] # Get updated party name.
        photo = request.files['photo'] # Get new photo file object (if uploaded).
        symbol = request.files['symbol'] # Get new symbol file object (if uploaded).
        
        # 1. Fetch existing candidate data to retain old file paths if no new file is uploaded
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,)) # Fetch current details before updating.
        candidate = cursor.fetchone() # Get the current record.
        election_id = candidate['election_id'] # Store the election ID for redirection.
        
        photo_path = candidate['photo_path'] # Start with the existing photo path.
        symbol_path = candidate['symbol_path'] # Start with the existing symbol path.
        
        # 2. Update photo if a new one is provided
        if photo and allowed_file(photo.filename): # Check if new photo uploaded and allowed.
            filename = secure_filename(photo.filename) # Clean the filename.
            new_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) # Define save path.
            photo.save(new_photo_path) # Save the new photo file.
            photo_path = filename # Update the path variable with the new filename.
        
        # 3. Update symbol if a new one is provided
        if symbol and allowed_file(symbol.filename): # Check if new symbol uploaded and allowed.
            filename = secure_filename(symbol.filename) # Clean the filename.
            new_symbol_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) # Define save path.
            symbol.save(new_symbol_path) # Save the new symbol file.
            symbol_path = filename # Update the path variable with the new filename.
        
        # 4. Update the database record
        cursor.execute( # Execute the UPDATE query to save new names and file paths.
            "UPDATE candidates SET candidate_name = %s, party_name = %s, photo_path = %s, symbol_path = %s WHERE id = %s",
            (candidate_name, party_name, photo_path, symbol_path, id)
        )
        conn.commit() # Commit the changes.
        flash('Candidate updated successfully!', 'success') # Flash success.
        return redirect(url_for('admin_candidates', election_id=election_id)) # Redirect to the candidate list.
    
    # GET request: fetch candidate data and render the edit form
    cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,)) # Fetch the candidate details by ID.
    candidate = cursor.fetchone() # Get the candidate record.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    
    return render_template('admin/edit_candidate.html', candidate=candidate) # Render the edit form, pre-filled with existing data.

# Delete Candidate
@app.route('/admin/candidate/delete/<int:id>') # Define route to delete a candidate by ID.
def delete_candidate(id): # Define the view function.
    """Deletes a candidate and all associated votes.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # 1. Get the election_id to redirect back to the correct candidate list
    cursor.execute("SELECT election_id FROM candidates WHERE id = %s", (id,)) # Get the election ID.
    candidate = cursor.fetchone() # Fetch the election ID row.
    election_id = candidate['election_id'] if candidate else None # Extract ID, or None if not found.

    # 2. Delete related votes first
    cursor.execute("DELETE FROM votes WHERE candidate_id = %s", (id,)) # Delete all votes cast for this candidate.
    # 3. Then, delete the candidate itself
    cursor.execute("DELETE FROM candidates WHERE id = %s", (id,)) # Delete the candidate record.
    conn.commit() # Commit deletion.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    
    flash('Candidate deleted successfully!', 'success') # Flash success.
    # Redirect back to the candidate list using the stored election_id.
    return redirect(url_for('admin_candidates', election_id=election_id))

# View Voters
@app.route('/admin/voters') # Define route to view voters.
def admin_voters(): # Define the view function.
    """Displays a list of all voters, optionally filtered by election linkage.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.

    # Get optional election_id filter from query parameters
    election_id = request.args.get('election_id', type=int) # Check if a filter for election_id is in the URL.
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # Load active elections for the assignment dropdown/filter
    cursor.execute("SELECT id, name FROM elections WHERE is_active = TRUE ORDER BY id DESC") # Fetch active elections for filter dropdown.
    elections = cursor.fetchall() # Fetch the list of active elections.

    if election_id: # If an election filter ID is provided:
        # If filtered: show voters linked to this specific election
        cursor.execute(""" # Select all voters that are linked to the specific election ID.
            SELECT v.* FROM voters v
            INNER JOIN election_voters ev ON ev.voter_id = v.id
            WHERE ev.election_id = %s
            ORDER BY v.id
        """, (election_id,))
    else:
        # If no filter: show all registered voters
        cursor.execute("SELECT * FROM voters ORDER BY id") # Select all voters in the system.

    voters = cursor.fetchall() # Fetch the list of voters (filtered or all).
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    # Render voter list page, passing voters, current filter ID, and active elections.
    return render_template('admin/voters.html', voters=voters, election_id=election_id, elections=elections)


@app.route('/admin/voter/add-to-election', methods=['POST']) # Define route to manually link a voter to an election (POST only).
def add_voter_to_election(): # Define the view function.
    """Manually links an existing voter to an election via POST request.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
        
    voter_id = request.form.get('voter_id', type=int) # Get voter ID from form.
    election_id = request.form.get('election_id', type=int) # Get election ID from form.
    if not voter_id or not election_id: # Validate that both IDs were received.
        flash('Invalid voter or election selection.', 'danger') # Flash error if validation fails.
        return redirect(url_for('admin_voters')) # Redirect to voter list.

    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor.
    # Check if the linkage already exists
    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, voter_id)) # Check junction table.
    if not cursor.fetchone(): # If linkage does not exist:
        # Create the linkage in the junction table
        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, voter_id)) # Insert the new link.
        conn.commit() # Commit the change.
        flash('Voter added to election successfully.', 'success') # Flash success.
    else:
        flash('Voter already assigned to that election.', 'info') # Flash info if already linked.

    cursor.close() # Close cursor.
    conn.close() # Close connection.
    # Redirect back to the voter list, filtered by the linked election.
    return redirect(url_for('admin_voters', election_id=election_id))


@app.route('/admin/election/<int:election_id>/upload-voters', methods=['GET', 'POST']) # Define route for bulk upload specific to an election (first version).
def upload_voters_for_election(election_id): # Define the view function.
    """
    Handles bulk uploading/linking voters via Excel file specifically to a single election.
    (This route seems redundant with the one below but handles file processing logic here).
    """ # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.

    if request.method == 'POST': # Process form submission.
        # (File validation and processing logic is similar to add_election route)
        if 'file' not in request.files: # Check if the expected file input ('file') is present.
            flash('No file part', 'danger') # Flash error.
            return redirect(request.url) # Redirect back to the upload page.
        # ... file validation checks ... (omitted for brevity)

        file = request.files['file'] # Get file object.
        if not (file and allowed_file(file.filename)): # Check if file is valid.
            flash('File error or type not allowed', 'danger') # Flash error.
            return redirect(request.url) # Redirect.

        # Use pandas to read the Excel file
        df = pd.read_excel(file) # Read file into DataFrame.
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns] # Normalize column names.

        inserted = 0 # Initialize counter.
        linked = 0 # Initialize counter.
        errors = 0 # Initialize counter.
        for index, row in df.iterrows(): # Loop through rows.
            try: # Start try block for row processing.
                # ... voter data extraction ... (omitted for brevity)
                full_name = str(row.get('full_name', '')).strip() # Extract full name.
                voter_id = str(row.get('voter_id', '')).strip() # Extract voter ID.
                email = str(row.get('email', '')).strip() # Extract email.
                password = str(row.get('password', '')).strip() # Extract password.
                if not (full_name and voter_id and email and password): # Check for required fields.
                    errors += 1 # Count error.
                    continue # Skip to next row.
                
                # Logic to check existence, link existing, or create new (identical to add_election)
                cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email)) # Check if voter exists.
                existing = cursor.fetchone() # Fetch result.
                
                if existing: # If voter exists:
                    vid = existing['id'] # Get voter ID.
                    # Link existing voter to election
                    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid)) # Check linkage.
                    if not cursor.fetchone(): # If not linked:
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid)) # Insert link.
                        linked += 1 # Increment linked counter.
                    else:
                        errors += 1 # Count skipped link.
                    continue # Next row.

                # Create new voter
                cursor.execute( # Insert new voter.
                    "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                    (full_name, voter_id, email, generate_password_hash(password)) # Hash password.
                )
                new_vid = cursor.lastrowid # Get new voter ID.
                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid)) # Link new voter.
                inserted += 1 # Increment inserted counter.
            except Exception: # Catch any processing error.
                errors += 1 # Count error.
                continue # Next row.

        conn.commit() # Commit all changes.
        flash(f'Voters processed: {inserted} new, {linked} linked, {errors} skipped.', 'success') # Flash summary.
        cursor.close() # Close cursor.
        conn.close() # Close connection.
        return redirect(url_for('admin_voters', election_id=election_id)) # Redirect to voter list.

    # GET -> show upload form
    cursor.execute("SELECT id, name, is_active FROM elections WHERE id = %s", (election_id,)) # Fetch election details.
    election = cursor.fetchone() # Get election row.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    return render_template('admin/upload_voters.html', election=election) # Render upload form.


@app.route('/admin/voters/upload/<int:election_id>', methods=['GET', 'POST']) # Define route for bulk upload (second version, uses file system).
def upload_voters(election_id): # Define the view function.
    """
    Another implementation for bulk voter upload and linking to an election.
    This version includes temporary file saving and cleanup.
    """ # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.

    # Check if election exists and is active
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE", (election_id,)) # Check election status.
    election = cursor.fetchone() # Fetch election.
    cursor.close() # Close cursor.
    conn.close() # Close initial connection/cursor before file handling
    
    if not election: # If election is not active:
        flash('Election not found or not active', 'danger') # Flash error.
        return redirect(url_for('admin_voters')) # Redirect.

    if request.method == 'GET': # If GET request:
        return render_template('admin/upload_voters.html', election=election) # Render upload form.

    # POST logic starts here
    if 'file' not in request.files: # Check for file.
        flash('No file selected', 'danger') # Flash error.
        return redirect(url_for('admin_voters')) # Redirect.
        
    file = request.files['file'] # Get file object.
    if file.filename == '' or not allowed_file(file.filename): # Check file validity.
        flash('Invalid file type or no file selected', 'danger') # Flash error.
        return redirect(url_for('admin_voters')) # Redirect.

    # Save file temporarily to disk for pandas to read
    filename = secure_filename(file.filename) # Clean filename.
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename) # Create full path.
    os.makedirs(os.path.dirname(filepath), exist_ok=True) # Ensure upload folder exists.
    file.save(filepath) # Save the file to disk.

    try: # Start try block for file reading and database operations.
        # Read file using pandas
        df = pd.read_excel(filepath, header=0) # Read Excel from saved file path.
        df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns] # Normalize columns.
        required_columns = {'full_name', 'voter_id', 'email', 'password'} # Define mandatory columns.
        missing = required_columns - set(df.columns) # Check for missing columns.
        if missing: # If mandatory columns are missing:
            flash(f'Missing required columns: {", ".join(missing)}', 'danger') # Flash error.
            return redirect(url_for('admin_voters')) # Redirect.

        # Re-establish connection for database transaction
        conn = get_db() # Get connection.
        cursor = conn.cursor() # Get simple cursor.
        inserted = 0 # Initialize counter.
        linked = 0 # Initialize counter.
        skipped = 0 # Initialize counter.

        for index, row in df.iterrows(): # Loop through all Excel rows.
            try: # Start inner try block for row processing.
                # ... same logic as above: extract, check existing, link, or create new voter ...
                full_name = str(row['full_name']).strip() # Extract data.
                voter_id = str(row['voter_id']).strip() # Extract data.
                email = str(row['email']).strip() # Extract data.
                password = str(row['password']).strip() # Extract data.
                if not all([full_name, voter_id, email, password]): # Check completeness.
                    skipped += 1 # Count skipped.
                    continue # Skip row.

                # Check existence
                cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email)) # Check voter existence.
                existing = cursor.fetchone() # Fetch result.
                
                if existing: # If voter exists:
                    vid = existing[0] # Get voter ID.
                    # Link existing to election
                    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid)) # Check linkage.
                    if not cursor.fetchone(): # If not linked:
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid)) # Insert link.
                        linked += 1 # Count link.
                    else:
                        skipped += 1 # Count skipped.
                    continue # Next row.

                # Create new voter
                cursor.execute( # Insert new voter.
                    "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                    (full_name, voter_id, email, generate_password_hash(password)) # Hash password.
                )
                new_vid = cursor.lastrowid # Get new voter ID.
                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid)) # Link new voter.
                inserted += 1 # Count inserted.

            except Exception: # Catch any row error.
                skipped += 1 # Count skipped.
                continue # Next row.

        conn.commit() # Commit all database changes.
        flash(f'Upload complete: {inserted} new, {linked} linked, {skipped} skipped.', 'success') # Flash summary.
        return redirect(url_for('admin_voters', election_id=election_id)) # Redirect to voter list.

    finally: # Execute this block regardless of success or failure.
        # Ensure the temporary uploaded file is deleted
        try: # Start try block for file deletion.
            if 'filepath' in locals() and os.path.exists(filepath): # Check if the filepath variable exists and the file is present.
                os.remove(filepath) # Delete the temporary file.
        except Exception: # Catch any error during file deletion.
            pass # Ignore deletion errors.


# Admin Results
@app.route('/admin/results/<int:election_id>') # Define route to view admin results.
def admin_results(election_id): # Define the view function.
    """Admin view of election results (always visible to admin).""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # Query: Get candidate details and count associated votes
    cursor.execute(""" # Execute query to count votes per candidate.
        SELECT c.id, c.candidate_name, c.party_name, c.photo_path, c.symbol_path, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id AND v.election_id = %s
        WHERE c.election_id = %s
        GROUP BY c.id
    """, (election_id, election_id))
    results = cursor.fetchall() # Fetch results.
    
    # Calculate total votes and percentages
    total_votes = sum(candidate['vote_count'] for candidate in results) if results else 0 # Calculate total votes.
    for candidate in results: # Loop through results.
        # Calculate percentage (preventing division by zero).
        candidate['percentage'] = round((candidate['vote_count'] / total_votes) * 100, 2) if total_votes > 0 else 0 
    
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    
    return render_template('admin/results.html', results=results, total_votes=total_votes, election_id=election_id) # Render admin results page.

@app.route('/admin/publish_results/<int:election_id>', methods=['POST']) # Define route to publish results globally.
def publish_results(election_id): # Define the view function.
    """Sets the global flag to allow all voters to view all election results.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
    
    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor.
    # Use UPSERT logic (INSERT or UPDATE) to set results_published to TRUE in the admin_settings table
    try: # Attempt the UPSERT (Insert On Duplicate Key Update).
        cursor.execute("INSERT INTO admin_settings (id, results_published) VALUES (1, TRUE) ON DUPLICATE KEY UPDATE results_published = TRUE")
    except Exception: # Catch exception if UPSERT is not supported or fails.
        # Fallback for older MySQL versions
        cursor.execute("UPDATE admin_settings SET results_published = TRUE WHERE id = 1") # Execute standard UPDATE.
        
    conn.commit() # Commit the change.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    flash('Results published!', 'success') # Flash success.
    return redirect(url_for('admin_results', election_id=election_id)) # Redirect back to the results view.


# Logout
@app.route('/logout') # Define the logout route.
def logout(): # Define the view function.
    """Clears the user session for both admin and voter.""" # Docstring.
    if 'admin_id' in session: # Check if admin is logged in.
        session.clear() # Clear the entire session data.
        flash("Admin logged out successfully.", "info") # Flash logout message.
        return redirect(url_for('admin_login')) # Redirect to admin login.

    elif 'voter_id' in session: # Check if voter is logged in.
        session.clear() # Clear the entire session data.
        flash("You have been logged out successfully.", "info") # Flash logout message.
        return redirect(url_for('voter_login')) # Redirect to voter login.

    session.clear() # Clear session just in case (handles unauthenticated user hitting /logout).
    return redirect(url_for('home')) # Redirect to the home page.

@app.route('/admin/archived-voters/<int:election_id>') # Define route to view archived voters for an election.
def archived_voters(election_id): # Define the view function.
    """Displays the snapshot of voters archived after an election was completed.""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.

    conn = get_db() # Get connection.
    cursor = conn.cursor(MySQLdb.cursors.DictCursor) # Get dict cursor.
    
    # Get election name for display
    cursor.execute("SELECT name FROM elections WHERE id = %s", (election_id,)) # Fetch election name.
    election = cursor.fetchone() # Get election row.
    
    # Fetch all archived voters for this specific election ID
    cursor.execute("SELECT * FROM archive_voters WHERE election_id = %s", (election_id,)) # Select all records from the archive table for this election.
    voters = cursor.fetchall() # Fetch all archived voters.
    
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    
    return render_template('admin/archived_voters.html', voters=voters, election=election) # Render the archived voter list.

@app.route('/admin/voter/delete/<int:id>') # Define route to delete a voter by ID.
def delete_voter(id): # Define the view function.
    """Deletes a voter record from the main voters table (linked records should cascade).""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
        
    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor.
    
    # Try to find the election_id for redirection purposes
    cursor.execute("SELECT election_id FROM election_voters WHERE voter_id = %s", (id,)) # Check if the voter is currently linked to any election.
    row = cursor.fetchone() # Fetch the first linkage ID.
    election_id = row[0] if row else None # Extract the election ID if found.
    
    # Delete the voter record
    cursor.execute("DELETE FROM voters WHERE id = %s", (id,)) # Delete the voter from the main table.
    conn.commit() # Commit the deletion.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    flash('Voter deleted successfully!', 'success') # Flash success.
    # Redirect back to the list they were viewing (all voters or filtered list).
    return redirect(url_for('admin_voters', election_id=election_id) if election_id else url_for('admin_voters'))

@app.route('/admin/election/delete/<int:election_id>', methods=['POST']) # Define route to delete an entire election (POST only).
def delete_election(election_id): # Define the view function.
    """Deletes an entire election and all related data (votes, candidates, archives).""" # Docstring.
    if 'admin_id' not in session: # Check admin login state.
        return redirect(url_for('admin_login')) # Redirect if not.
        
    conn = get_db() # Get connection.
    cursor = conn.cursor() # Get simple cursor.
    
    # Delete all associated data in a cascade-like manner
    cursor.execute("DELETE FROM archive_voters WHERE election_id = %s", (election_id,)) # Delete archived records.
    cursor.execute("DELETE FROM votes WHERE election_id = %s", (election_id,)) # Delete votes associated with this election.
    cursor.execute("DELETE FROM candidates WHERE election_id = %s", (election_id,)) # Delete candidates for this election.
    # Delete linkages in junction table (assuming voters are not deleted)
    cursor.execute("DELETE FROM election_voters WHERE election_id = %s", (election_id,)) # Delete voter-election links.
    # Finally, delete the election itself
    cursor.execute("DELETE FROM elections WHERE id = %s", (election_id,)) # Delete the main election record.
    
    conn.commit() # Commit all deletions.
    cursor.close() # Close cursor.
    conn.close() # Close connection.
    flash('Election and all related data deleted successfully!', 'success') # Flash success.
    return redirect(url_for('admin_elections')) # Redirect to the elections list.


if __name__ == '__main__': # Standard Python entry point check.
    app.run(debug=True) # Run the Flask application in debug mode (allows automatic code reloading).
