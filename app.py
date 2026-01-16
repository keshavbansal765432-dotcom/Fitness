from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

### Database setup
def get_db():
    conn = sqlite3.connect("users.db")
    return conn

# Create table if not exists
def init_db():
    with get_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            bio TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['full name']
        bio = request.form['bio']
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, email, password, full_name, bio) VALUES (?, ?, ?, ?, ?)", 
                             (username, email, password, fullname, bio))
            return redirect(url_for('dashboard'))
        except:
            return render_template('register.html', error="Username or email already taken")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
            if user:
                session['user'] = username
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

# Example view_challenges endpoint -- connect your actual challenge logic here!
@app.route('/challenge_index')
def challenge_index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user = session['user'])


@app.route('/leaderboard')
def leaderboard():
    conn = get_db()        # or your connection function
    c = conn.cursor()
    # Join with users table for username if you have one, else use email
    c.execute("""
        SELECT users.username, SUM(
            CASE challenges.difficulty
                WHEN 'easy' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'hard' THEN 5
                ELSE 0
            END
        ) as points
        FROM completed_challenges
        JOIN challenges ON completed_challenges.challenge_id = challenges.id
        JOIN users ON completed_challenges.email = users.email
        GROUP BY users.username
        ORDER BY points DESC, users.username ASC
    """)
    leaderboard = c.fetchall()
    conn.close()
    return render_template('leaderboard.html', leaderboard=leaderboard)

@app.route('/tips', methods=['GET', 'POST'])
def tips():
    print("🎯 TIPS ROUTE HIT!")
    
    # Handle POST (new tip)
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if 'user_id' in session:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO tips (user_id, title, content) VALUES (?, ?, ?)", 
                      (session['user_id'], title, content))
            conn.commit()
            conn.close()
            print(f"✅ Tip posted: {title}")
    
    # Get filter from URL params (default: newest)
    sort = request.args.get('sort', 'newest')
    print(f"🔍 Filter: {sort}")
    
    # Fetch tips with filter
    conn = get_db()
    c = conn.cursor()
    
    if sort == 'newest':
        c.execute("SELECT id, title, content, created_at FROM tips ORDER BY created_at DESC")
    elif sort == 'oldest':
        c.execute("SELECT id, title, content, created_at FROM tips ORDER BY created_at ASC")
    else:
        c.execute("SELECT id, title, content, created_at FROM tips ORDER BY created_at DESC")
    
    tips_list = c.fetchall()
    print(f"📊 Showing {len(tips_list)} tips ({sort})")
    conn.close()
    
    return render_template('tip.html', tips=tips_list, sort=sort)

def setup_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        title TEXT UNIQUE,
        description TEXT,
        deadline TEXT,
        difficulty TEXT,
        FOREIGN KEY(username) REFERENCES users(username),
        FOREIGN KEY(email) REFERENCES users(email)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS accepted_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        challenge_id INTEGER,
        FOREIGN KEY(challenge_id) REFERENCES challenges(id),
        FOREIGN KEY(username) REFERENCES users(username),
        FOREIGN KEY(email) REFERENCES users(email)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS completed_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        challenge_id INTEGER,
        FOREIGN KEY(challenge_id) REFERENCES challenges(id),
        FOREIGN KEY(username) REFERENCES users(username),
        FOREIGN KEY(email) REFERENCES users(email)
    )''')
    c.execute("""
    CREATE TABLE IF NOT EXISTS tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user INTEGER,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()


setup_db()

def has_accepted(email, challenge_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM accepted_challenges WHERE email=? AND challenge_id=?', (email, challenge_id))
    found = c.fetchone() is not None
    conn.close()
    return found

@app.route('/post_challenge', methods=['GET', 'POST'])
def post_challenge():
    if request.method == 'POST':
        email = request.form.get('email')
        title = request.form.get('title')
        description = request.form.get('description')
        deadline = request.form.get('deadline')
        difficulty = request.form.get('difficulty')
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO challenges (email, title, description, deadline, difficulty) VALUES (?, ?, ?, ?, ?)',
                  (email, title, description, deadline, difficulty))
        conn.commit()
        conn.close()
        return redirect(url_for('view_challenge', email=email))
    return render_template('post_challenge.html')

@app.route('/view_challenge')
def view_challenge():
    email = request.args.get('email', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, title FROM challenges')
    challenges = c.fetchall()
    conn.close()
    challenge_status = {}
    for ch in challenges:
        challenge_status[ch[0]] = "accepted" if has_accepted(email, ch[0]) else None
    return render_template('view_challenge.html', challenges=challenges, email=email, challenge_status=challenge_status)

@app.route('/accept_challenge/<int:challenge_id>')
def accept_challenge(challenge_id):
    email = request.args.get('email', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM accepted_challenges WHERE email=? AND challenge_id=?', (email, challenge_id))
    if not c.fetchone():
        c.execute('INSERT INTO accepted_challenges (email, challenge_id) VALUES (?, ?)', (email, challenge_id))
        conn.commit()
    conn.close()
    return redirect(url_for('view_accepted_challenge', email=email))

@app.route('/view_accepted_challenge')
def view_accepted_challenge():
    email = request.args.get('email', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT challenges.title, challenges.id
                 FROM accepted_challenges
                 JOIN challenges ON accepted_challenges.challenge_id = challenges.id
                 WHERE accepted_challenges.email=?''', (email,))
    challenges = c.fetchall()
    conn.close()
    return render_template('view_accepted_challenge.html', challenges=challenges, email=email)

@app.route('/complete_challenge/<int:challenge_id>')
def complete_challenge(challenge_id):
    email = request.args.get('email', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM accepted_challenges WHERE email=? AND challenge_id=?', (email, challenge_id))
    c.execute('SELECT 1 FROM completed_challenges WHERE email=? AND challenge_id=?', (email, challenge_id))
    if not c.fetchone():
        c.execute('INSERT INTO completed_challenges (email, challenge_id) VALUES (?, ?)', (email, challenge_id))
    conn.commit()
    conn.close()
    return redirect(url_for('view_completed_challenge', email=email))

@app.route('/view_completed_challenge')
def view_completed_challenge():
    email = request.args.get('email', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT challenges.title, challenges.id
                 FROM completed_challenges
                 JOIN challenges ON completed_challenges.challenge_id = challenges.id
                 WHERE completed_challenges.email=?''', (email,))
    challenges = c.fetchall()
    conn.close()
    return render_template('view_completed_challenges.html', challenges=challenges, email=email)

@app.route('/challenge_info/<int:challenge_id>')
def challenge_info(challenge_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT title, description, deadline, difficulty FROM challenges WHERE id=?', (challenge_id,))
    challenge = c.fetchone()
    conn.close()
    return render_template('challenge_info.html', challenge=challenge)

if __name__ == '__main__':
    app.run(debug=True)
