import os
import pandas as pd
from datetime import datetime

import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
import cv2
import numpy as np


app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# Database connection
def get_db():
    return MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB']
    )

# Allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Home route
@app.route('/')
def home():
    return redirect(url_for('voter_login'))

# --------------------- Voter Routes ---------------------

def capture_and_verify_face():
    """Capture face from webcam using OpenCV"""
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return False
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
        cv2.imshow('Face Verification - Look at camera (Press SPACE to verify, Q to quit)', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' ') and len(faces) > 0:
            cap.release()
            cv2.destroyAllWindows()
            return True
    
    cap.release()
    cv2.destroyAllWindows()
    return False


# ...existing imports...

def get_face_features(frame, face_cascade):
    """Extract face features using HOG descriptor"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) == 0:
        return None
        
    (x, y, w, h) = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (128, 128))
    
    # Calculate HOG features
    hog = cv2.HOGDescriptor()
    features = hog.compute(face)
    return features

def compare_faces(stored_features, current_features, threshold=0.80 ):
    """Compare face features using cosine similarity"""
    if stored_features is None or current_features is None:
        return False
    
    # Convert bytes to numpy arrays if stored in database
    if isinstance(stored_features, bytes):
        stored_features = np.frombuffer(stored_features, dtype=np.float32)
    
    # Calculate cosine similarity
    similarity = np.dot(stored_features.flatten(), current_features.flatten()) / \
                (np.linalg.norm(stored_features) * np.linalg.norm(current_features))
    
    return similarity > threshold

@app.route('/voter/register', methods=['GET', 'POST'])
def voter_register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        voter_id = request.form['voter_id']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        cap = cv2.VideoCapture(0)
        face_features = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                flash('Camera error!', 'danger')
                return redirect(url_for('voter_register'))
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            cv2.imshow('Look directly at camera (Press SPACE when ready)', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' ') and len(faces) > 0:
                face_features = get_face_features(frame, face_cascade)
                if face_features is not None:
                    break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if face_features is None:
            flash('Face registration failed. Please try again.', 'danger')
            return redirect(url_for('voter_register'))
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO voters (full_name, voter_id, email, password, face_features) VALUES (%s, %s, %s, %s, %s)",
                (full_name, voter_id, email, password, face_features.tobytes())
            )
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('voter_login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('voter/register.html')

@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            cursor.execute(
                "SELECT * FROM voters WHERE email = %s OR voter_id = %s",
                (identifier, identifier)
            )
            voter = cursor.fetchone()
            
            if voter and check_password_hash(voter['password'], password):
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                cap = cv2.VideoCapture(0)
                verification_attempts = 0
                max_attempts = 3
                
                while verification_attempts < max_attempts:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    cv2.imshow(f'Face Verification (Attempt {verification_attempts + 1}/{max_attempts})', frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord(' ') and len(faces) > 0:
                        current_features = get_face_features(frame, face_cascade)
                        if current_features is not None and compare_faces(voter['face_features'], current_features):
                            cap.release()
                            cv2.destroyAllWindows()
                            session['voter_id'] = voter['id']
                            flash('Login successful!', 'success')
                            return redirect(url_for('voter_dashboard'))
                        verification_attempts += 1
                    elif key == ord('q'):
                        break
                
                cap.release()
                cv2.destroyAllWindows()
                flash('Face verification failed!', 'danger')
            else:
                flash('Invalid credentials!', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('voter/login.html')


# Voter Dashboard
@app.route('/voter/dashboard')
def voter_dashboard():
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT has_voted FROM voters WHERE id = %s", (session['voter_id'],))
    voter = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('voter/dashboard.html', voter=voter)


@app.route('/voter/elections')
def voter_elections():
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    now = datetime.now()
    # Show elections that are active and started but not ended
    cursor.execute("SELECT * FROM elections WHERE is_active = TRUE AND start_time <= %s AND end_time >= %s", (now, now))
    elections = cursor.fetchall()
    cursor.close()
    conn.close()

    if not elections:
        flash('No active elections available at the moment.', 'info')
    return render_template('voter/elections.html', elections=elections)

# View Candidates
@app.route('/voter/candidates/<int:election_id>')
def voter_candidates(election_id):
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # Check if election is active and within time
    from datetime import datetime
    now = datetime.now()
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE AND start_time <= %s AND end_time >= %s", (election_id, now, now))
    election = cursor.fetchone()
    if not election:
        flash('This election is not active or not within the voting time!', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_elections'))

    # Get candidates for this election
    cursor.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,))
    candidates = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('voter/candidates.html', candidates=candidates, election=election)

@app.route('/voter/results/select')
def voter_results_select():
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Check global publish flag. If results are published, show all elections (so voters can view results).
    cursor.execute("SELECT results_published FROM admin_settings WHERE id = 1")
    settings = cursor.fetchone()

    if settings and settings.get('results_published'):
        # Results published: show all elections (ordered by end_time)
        cursor.execute("SELECT * FROM elections ORDER BY end_time DESC")
    else:
        # Results not published: only show elections that have ended / been marked inactive
        cursor.execute("SELECT * FROM elections WHERE is_active = FALSE ORDER BY end_time DESC")

    elections = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('voter/results_select.html', elections=elections)


# Cast Vote
@app.route('/vote/<int:candidate_id>', methods=['POST'])
def cast_vote(candidate_id):
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))

    election_id = request.form.get('election_id')
    if not election_id:
        flash('Election not specified!', 'danger')
        return redirect(url_for('voter_dashboard'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Ensure election exists and is active (or within allowed voting window)
    now = datetime.now()
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE AND (start_time IS NULL OR start_time <= %s) AND (end_time IS NULL OR end_time >= %s)", (election_id, now, now))
    election = cursor.fetchone()
    if not election:
        cursor.close()
        conn.close()
        flash('This election is not active or not within the voting time!', 'warning')
        return redirect(url_for('voter_dashboard'))

    # Ensure the voter is registered/linked to this election
    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, session['voter_id']))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        flash('You are not registered for this election. You cannot vote.', 'danger')
        return redirect(url_for('voter_dashboard'))

    # Check if voter has already voted in this election
    cursor.execute(
        "SELECT * FROM votes WHERE voter_id = %s AND election_id = %s",
        (session['voter_id'], election_id)
    )
    already_voted = cursor.fetchone()
    if already_voted:
        flash('You have already voted in this election!', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_dashboard'))

    try:
        # Record vote
        cursor.execute(
            "INSERT INTO votes (voter_id, candidate_id, election_id) VALUES (%s, %s, %s)",
            (session['voter_id'], candidate_id, election_id)
        )
        # Update voter status (optional: if you want to track per-election voting, adjust schema)
        cursor.execute(
            "UPDATE voters SET has_voted = 1 WHERE id = %s",
            (session['voter_id'],)
        )
        conn.commit()
        flash('Vote cast successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('voter_results', election_id=election_id))


# View Results
@app.route('/voter/results/<int:election_id>')
def voter_results(election_id):
    if 'voter_id' not in session:
        return redirect(url_for('voter_login'))
    
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # Load global publish flag and election details
    cursor.execute("SELECT results_published FROM admin_settings WHERE id = 1")
    settings = cursor.fetchone()

    cursor.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
    election = cursor.fetchone()
    if not election:
        flash('Election not found!', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_results_select'))

    # Allow viewing if admin published results OR the election has ended / been marked inactive
    now = datetime.now()
    results_published = bool(settings and settings.get('results_published'))
    election_ended = (not election.get('is_active')) or (election.get('end_time') is not None and election.get('end_time') <= now)

    if not results_published and not election_ended:
        flash('Results are not published yet!', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_dashboard'))
    
    cursor.execute("""
    SELECT c.id, c.candidate_name, c.party_name, c.photo_path, c.symbol_path, COUNT(v.id) AS vote_count
    FROM candidates c
    LEFT JOIN votes v ON c.id = v.candidate_id AND v.election_id = %s
    WHERE c.election_id = %s
    GROUP BY c.id
    """, (election_id, election_id))
    
    results = cursor.fetchall()
    total_votes = sum(candidate['vote_count'] for candidate in results) if results else 0
    for candidate in results:
        candidate['percentage'] = round((candidate['vote_count'] / total_votes) * 100, 2) if total_votes > 0 else 0
    
    cursor.close()
    conn.close()
    
    return render_template('voter/results.html', results=results, total_votes=total_votes)
# --------------------- Admin Routes ---------------------

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if admin and admin['password'] == password:
            session['admin_id'] = admin['id']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('admin/login.html')

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor()
    # Get counts
    cursor.execute("SELECT COUNT(*) FROM voters")
    voters_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM candidates")
    candidates_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM votes")
    votes_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return render_template('admin/dashboard.html', 
                          voters_count=voters_count,
                          candidates_count=candidates_count,
                          votes_count=votes_count)

#add election

# ...existing code...
@app.route('/admin/election/add', methods=['GET', 'POST'])
def add_election():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        election_name = request.form['name']
        area = request.form['area']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        conn = get_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "INSERT INTO elections (name, area, start_time, end_time, is_active) VALUES (%s, %s, %s, %s, TRUE)",
            (election_name, area, start_time, end_time)
        )
        election_id = cursor.lastrowid

        # Handle voters list upload (reuse existing voters or create new + link)
        inserted = 0
        linked = 0
        errors = 0
        if 'voters_file' in request.files:
            file = request.files['voters_file']
            if file and allowed_file(file.filename):
                df = pd.read_excel(file)
                df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                for index, row in df.iterrows():
                    try:
                        full_name = str(row.get('full_name', '')).strip()
                        voter_id = str(row.get('voter_id', '')).strip()
                        email = str(row.get('email', '')).strip()
                        password = str(row.get('password', '')).strip()
                        if not (full_name and voter_id and email and password):
                            errors += 1
                            continue

                        # find existing voter by voter_id or email
                        cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email))
                        existing = cursor.fetchone()
                        if existing:
                            vid = existing['id']
                            # link if not already linked
                            cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid))
                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid))
                                linked += 1
                            else:
                                # already linked
                                errors += 1
                            continue

                        # create new voter then link
                        cursor.execute(
                            "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                            (full_name, voter_id, email, generate_password_hash(password))
                        )
                        new_vid = cursor.lastrowid
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid))
                        inserted += 1
                    except Exception:
                        errors += 1
                        continue

        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Election created. {inserted} new voters added, {linked} existing voters linked, {errors} skipped.', 'success')
        return redirect(url_for('admin_elections'))

    return render_template('admin/add_elections.html')
# ...existing code...

@app.route('/admin/elections', methods=['GET', 'POST'])
def admin_elections():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM elections ORDER BY id DESC")
    elections = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/elections.html', elections=elections)

# ...existing code...
@app.route('/admin/election/complete/<int:election_id>', methods=['POST'])
def complete_election(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor()

    # mark election inactive
    cursor.execute("UPDATE elections SET is_active = FALSE WHERE id = %s", (election_id,))

    # Archive voters linked to this election (snapshot) — do NOT delete voters
    cursor.execute("""
        INSERT INTO archive_voters (full_name, voter_id, email, password, has_voted, registered_at, election_id)
        SELECT v.full_name, v.voter_id, v.email, v.password, v.has_voted, v.registered_at, ev.election_id
        FROM voters v
        JOIN election_voters ev ON ev.voter_id = v.id
        WHERE ev.election_id = %s
    """, (election_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Election completed and voters archived (snapshot). Voters remain in system for future elections.', 'success')
    return redirect(url_for('admin_elections'))
# ...existing code...

# Manage Candidates
@app.route('/admin/candidate/add/<int:election_id>', methods=['GET', 'POST'])
def add_candidate(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # Get the current election info
    cursor.execute("SELECT id, name FROM elections WHERE id = %s", (election_id,))
    election = cursor.fetchone()

    if request.method == 'POST':
        candidate_name = request.form['candidate_name']
        party_name = request.form['party_name']
        photo = request.files['photo']
        symbol = request.files['symbol']

        photo_path = None
        symbol_path = None

        # Save photo
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_path = filename

        # Save symbol
        if symbol and allowed_file(symbol.filename):
            filename = secure_filename(symbol.filename)
            symbol.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            symbol_path = filename

        cursor.execute(
            "INSERT INTO candidates (candidate_name, party_name, photo_path, symbol_path, election_id) VALUES (%s, %s, %s, %s, %s)",
            (candidate_name, party_name, photo_path, symbol_path, election_id)
        )
        conn.commit()
        flash('Candidate added successfully!', 'success')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_candidates', election_id=election_id))

    cursor.close()
    conn.close()
    # Pass only the current election to the template
    return render_template('admin/add_candidates.html', election=election, election_id=election_id)

@app.route('/admin/candidates/<int:election_id>')
def admin_candidates(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,))
    candidates = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/candidates.html', candidates=candidates, election_id=election_id)

# Edit Candidate
@app.route('/admin/candidate/edit/<int:id>', methods=['GET', 'POST'])
def edit_candidate(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        candidate_name = request.form['candidate_name']
        party_name = request.form['party_name']
        photo = request.files['photo']
        symbol = request.files['symbol']
        
        # Get existing data
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,))
        candidate = cursor.fetchone()
        election_id = candidate['election_id']
        
        photo_path = candidate['photo_path']
        symbol_path = candidate['symbol_path']
        
        # Update photo if provided
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            new_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(new_photo_path)
            photo_path = filename
        
        # Update symbol if provided
        if symbol and allowed_file(symbol.filename):
            filename = secure_filename(symbol.filename)
            new_symbol_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            symbol.save(new_symbol_path)
            symbol_path = filename
        
        cursor.execute(
            "UPDATE candidates SET candidate_name = %s, party_name = %s, photo_path = %s, symbol_path = %s WHERE id = %s",
            (candidate_name, party_name, photo_path, symbol_path, id)
        )
        conn.commit()
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('admin_candidates', election_id=election_id))
    
    cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,))
    candidate = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('admin/edit_candidate.html', candidate=candidate)

# Delete Candidate
@app.route('/admin/candidate/delete/<int:id>')
def delete_candidate(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # Get the election_id before deleting
    cursor.execute("SELECT election_id FROM candidates WHERE id = %s", (id,))
    candidate = cursor.fetchone()
    election_id = candidate['election_id'] if candidate else None

    # First, delete votes for this candidate
    cursor2 = conn.cursor()
    cursor2.execute("DELETE FROM votes WHERE candidate_id = %s", (id,))
    # Then, delete the candidate
    cursor2.execute("DELETE FROM candidates WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    cursor2.close()
    conn.close()
    
    flash('Candidate deleted successfully!', 'success')
    # Redirect with election_id
    return redirect(url_for('admin_candidates', election_id=election_id))

# View Voters

# ...existing code...
@app.route('/admin/voters')
def admin_voters():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    election_id = request.args.get('election_id', type=int)
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    # load active elections for assignment dropdown
    cursor.execute("SELECT id, name FROM elections WHERE is_active = TRUE ORDER BY id DESC")
    elections = cursor.fetchall()

    if election_id:
        # show voters linked to this election using election_voters
        cursor.execute("""
            SELECT v.* FROM voters v
            INNER JOIN election_voters ev ON ev.voter_id = v.id
            WHERE ev.election_id = %s
            ORDER BY v.id
        """, (election_id,))
    else:
        # show all voters
        cursor.execute("SELECT * FROM voters ORDER BY id")

    voters = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/voters.html', voters=voters, election_id=election_id, elections=elections)


@app.route('/admin/voter/add-to-election', methods=['POST'])
def add_voter_to_election():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    voter_id = request.form.get('voter_id', type=int)
    election_id = request.form.get('election_id', type=int)
    if not voter_id or not election_id:
        flash('Invalid voter or election selection.', 'danger')
        return redirect(url_for('admin_voters'))

    conn = get_db()
    cursor = conn.cursor()
    # ensure not already linked
    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, voter_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, voter_id))
        conn.commit()
        flash('Voter added to election successfully.', 'success')
    else:
        flash('Voter already assigned to that election.', 'info')

    cursor.close()
    conn.close()
    return redirect(url_for('admin_voters', election_id=election_id))
# ...existing code...


# ...existing code...
@app.route('/admin/election/<int:election_id>/upload-voters', methods=['GET', 'POST'])
def upload_voters_for_election(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('File type not allowed', 'danger')
            return redirect(request.url)

        df = pd.read_excel(file)
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

        inserted = 0
        linked = 0
        errors = 0
        for index, row in df.iterrows():
            try:
                full_name = str(row.get('full_name', '')).strip()
                voter_id = str(row.get('voter_id', '')).strip()
                email = str(row.get('email', '')).strip()
                password = str(row.get('password', '')).strip()
                if not (full_name and voter_id and email and password):
                    errors += 1
                    continue

                cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email))
                existing = cursor.fetchone()
                if existing:
                    vid = existing['id']
                    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid))
                        linked += 1
                    else:
                        errors += 1
                    continue

                cursor.execute(
                    "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                    (full_name, voter_id, email, generate_password_hash(password))
                )
                new_vid = cursor.lastrowid
                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid))
                inserted += 1
            except Exception:
                errors += 1
                continue

        conn.commit()
        flash(f'Voters processed: {inserted} new, {linked} linked, {errors} skipped.', 'success')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_voters', election_id=election_id))

    # GET -> show upload form
    cursor.execute("SELECT id, name, is_active FROM elections WHERE id = %s", (election_id,))
    election = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('admin/upload_voters.html', election=election)
# ...existing code...

# ...existing code...
@app.route('/admin/voters/upload/<int:election_id>', methods=['GET', 'POST'])
def upload_voters(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    # Check if election exists and is active
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = TRUE", (election_id,))
    election = cursor.fetchone()
    cursor.close()
    conn.close()

    if not election:
        flash('Election not found or not active', 'danger')
        return redirect(url_for('admin_voters'))

    if request.method == 'GET':
        # provide the election object to the template (template expects `election`)
        return render_template('admin/upload_voters.html', election=election)

    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('admin_voters'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('admin_voters'))
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload an Excel file (.xlsx, .xls)', 'danger')
        return redirect(url_for('admin_voters'))

    # Save file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    try:
        df = pd.read_excel(filepath, header=0)
        df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
        required_columns = {'full_name', 'voter_id', 'email', 'password'}
        missing = required_columns - set(df.columns)
        if missing:
            flash(f'Missing required columns: {", ".join(missing)}', 'danger')
            return redirect(url_for('admin_voters'))

        conn = get_db()
        cursor = conn.cursor()
        inserted = 0
        linked = 0
        skipped = 0

        for index, row in df.iterrows():
            try:
                full_name = str(row['full_name']).strip()
                voter_id = str(row['voter_id']).strip()
                email = str(row['email']).strip()
                password = str(row['password']).strip()
                if not all([full_name, voter_id, email, password]):
                    skipped += 1
                    continue

                # find existing voter by voter_id or email
                cursor.execute("SELECT id FROM voters WHERE voter_id = %s OR email = %s", (voter_id, email))
                existing = cursor.fetchone()
                if existing:
                    vid = existing[0]
                    # link to election if not already linked
                    cursor.execute("SELECT 1 FROM election_voters WHERE election_id = %s AND voter_id = %s", (election_id, vid))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, vid))
                        linked += 1
                    else:
                        skipped += 1
                    continue

                # create new voter
                cursor.execute(
                    "INSERT INTO voters (full_name, voter_id, email, password, has_voted, registered_at) VALUES (%s, %s, %s, %s, 0, NOW())",
                    (full_name, voter_id, email, generate_password_hash(password))
                )
                new_vid = cursor.lastrowid
                cursor.execute("INSERT INTO election_voters (election_id, voter_id) VALUES (%s, %s)", (election_id, new_vid))
                inserted += 1

            except Exception:
                skipped += 1
                continue

        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Upload complete: {inserted} new, {linked} linked, {skipped} skipped.', 'success')
        return redirect(url_for('admin_voters', election_id=election_id))

    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
# ...existing code...`


# Admin Results
@app.route('/admin/results/<int:election_id>')
def admin_results(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Get vote counts
    cursor.execute("""
        SELECT c.id, c.candidate_name, c.party_name, c.photo_path, c.symbol_path, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id AND v.election_id = %s
        WHERE c.election_id = %s
        GROUP BY c.id
    """, (election_id, election_id))
    results = cursor.fetchall()
    
    # Calculate total votes
    total_votes = sum(candidate['vote_count'] for candidate in results) if results else 0
    
    # Calculate percentages
    for candidate in results:
        candidate['percentage'] = round((candidate['vote_count'] / total_votes) * 100, 2) if total_votes > 0 else 0
    
    cursor.close()
    conn.close()
    
    return render_template('admin/results.html', results=results, total_votes=total_votes, election_id=election_id)

@app.route('/admin/publish_results/<int:election_id>', methods=['POST'])
def publish_results(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    # Ensure admin_settings row exists; insert or update (upsert)
    try:
        cursor.execute("INSERT INTO admin_settings (id, results_published) VALUES (1, TRUE) ON DUPLICATE KEY UPDATE results_published = TRUE")
    except Exception:
        # Fallback to update if INSERT ... ON DUPLICATE KEY is not supported or fails
        cursor.execute("UPDATE admin_settings SET results_published = TRUE WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    flash('Results published!', 'success')
    return redirect(url_for('admin_results', election_id=election_id))


# Logout
@app.route('/logout')
def logout():
    # If admin is logged in
    if 'admin_id' in session:
        session.clear()
        flash("Admin logged out successfully.", "info")
        return redirect(url_for('admin_login'))

    # If voter is logged in
    elif 'voter_id' in session:
        session.clear()
        flash("You have been logged out successfully.", "info")
        return redirect(url_for('voter_login'))

    # If no one is logged in, just go home
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin/archived-voters/<int:election_id>')
def archived_voters(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Get election details
    cursor.execute("SELECT name FROM elections WHERE id = %s", (election_id,))
    election = cursor.fetchone()
    
    # Get archived voters (fetch all columns)
    cursor.execute("SELECT * FROM archive_voters WHERE election_id = %s", (election_id,))
    voters = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/archived_voters.html', voters=voters, election=election)

@app.route('/admin/voter/delete/<int:id>')
def delete_voter(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    # Optionally get election_id to redirect back to the correct list
    cursor.execute("SELECT election_id FROM voters WHERE id = %s", (id,))
    row = cursor.fetchone()
    election_id = row[0] if row else None
    cursor.execute("DELETE FROM voters WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Voter deleted successfully!', 'success')
    return redirect(url_for('admin_voters', election_id=election_id) if election_id else url_for('admin_voters'))

@app.route('/admin/election/delete/<int:election_id>', methods=['POST'])
def delete_election(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    # Delete from archive_voters first (if any)
    cursor.execute("DELETE FROM archive_voters WHERE election_id = %s", (election_id,))
    # Delete from votes (cascades with foreign keys, but explicit is safe)
    cursor.execute("DELETE FROM votes WHERE election_id = %s", (election_id,))
    # Delete from candidates
    cursor.execute("DELETE FROM candidates WHERE election_id = %s", (election_id,))
    # Delete from voters
    cursor.execute("DELETE FROM voters WHERE election_id = %s", (election_id,))
    # Finally, delete the election itself
    cursor.execute("DELETE FROM elections WHERE id = %s", (election_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Election and all related data deleted successfully!', 'success')
    return redirect(url_for('admin_elections'))



if __name__ == '__main__':
    app.run(debug=True)
