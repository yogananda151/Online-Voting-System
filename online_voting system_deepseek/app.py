import os
import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config

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

# Voter Registration
@app.route('/voter/register', methods=['GET', 'POST'])
def voter_register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        voter_id = request.form['voter_id']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO voters (full_name, voter_id, email, password) VALUES (%s, %s, %s, %s)",
                (full_name, voter_id, email, password)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('voter_login'))
        except MySQLdb.IntegrityError:
            flash('Voter ID or Email already exists!', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('voter/register.html')

# Voter Login
@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM voters WHERE email = %s OR voter_id = %s",
            (identifier, identifier)
        )
        voter = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if voter and check_password_hash(voter['password'], password):
            session['voter_id'] = voter['id']
            session['voter_name'] = voter['full_name']
            return redirect(url_for('voter_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
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
    from datetime import datetime
    now = datetime.now()
    cursor.execute("SELECT * FROM elections WHERE is_active = TRUE AND start_time <= %s AND end_time >= %s", (now, now))
    elections = cursor.fetchall()
    cursor.close()
    conn.close()
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
    cursor.execute("SELECT results_published FROM admin_settings WHERE id = 1")
    settings = cursor.fetchone()
    if not settings or not settings['results_published']:
        flash('Results are not published yet!', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_dashboard'))
    
    # Check if election exists and is completed
    cursor.execute("SELECT * FROM elections WHERE id = %s AND is_active = FALSE", (election_id,))
    completed_election = cursor.fetchone()
    if not completed_election:
        flash('Election not found or not completed!', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('voter_results_select'))
    
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
@app.route('/admin/election/add', methods=['GET', 'POST'])
def add_election():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        election_name = request.form['election_name']
        area = request.form['area']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO elections (name, area, start_time, end_time) VALUES (%s, %s, %s, %s)",
            (election_name, area, start_time, end_time)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Election created!', 'success')
        return redirect(url_for('admin_elections'))
    return render_template('admin/add_elections.html')


@app.route('/admin/elections', methods=['GET', 'POST'])
def admin_elections():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/elections.html', elections=elections)

@app.route('/admin/election/complete/<int:election_id>', methods=['POST'])
def complete_election(election_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE elections SET is_active = FALSE WHERE id = %s", (election_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Voting completed for this election!', 'success')
    return redirect(url_for('admin_elections'))



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
# In your admin_voters route:
@app.route('/admin/voters')
def admin_voters():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM voters")
    voters = cursor.fetchall()

    # Get active election
    cursor.execute("SELECT id FROM elections WHERE is_active = TRUE LIMIT 1")
    active_election = cursor.fetchone()
    election_id = active_election['id'] if active_election else None

    # For each voter, check if they have voted in the current election
    for voter in voters:
        cursor.execute("SELECT id FROM votes WHERE voter_id = %s AND election_id = %s", (voter['id'], election_id))
        voter['has_voted'] = bool(cursor.fetchone())

    cursor.close()
    conn.close()

    return render_template('admin/voters.html', voters=voters)

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
    cursor.execute("UPDATE admin_settings SET results_published = TRUE WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    flash('Results published!', 'success')
    return redirect(url_for('admin_results', election_id=election_id))


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)