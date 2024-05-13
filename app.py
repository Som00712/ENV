from flask import Flask, render_template, request, redirect, url_for, session, Response, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

# Initialize Flask application
app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key'

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'myuser'
app.config['MYSQL_PASSWORD'] = 'mypassword'
app.config['MYSQL_DB'] = 'Quozio'
mysql = MySQL(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT UserID, Username FROM Users WHERE Username = %s AND PasswordHash = %s', (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['UserID']
            session['username'] = account['Username']
            msg = 'Logged in successfully!'
            return redirect(url_for('login'))  # Redirect to login page
        else:
            msg = 'Incorrect username or password!'
    return render_template('index.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if 'username' in request.form and 'password' in request.form and 'role' in request.form:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT UserID, Username, Role FROM Users WHERE Username = %s AND PasswordHash = %s AND Role = %s', (username, password, role))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['UserID']
            session['username'] = account['Username']
            session['Role'] = account['Role']
            msg = 'Logged in successfully!'
            role = account['Role']
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            msg = 'Incorrect username/password/role!'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    default_role = 'student'  # Set the default role for all new registrations
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE Username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO Users (Username, Email, PasswordHash, Role) VALUES (%s, %s, %s, %s)', (username, email, password, default_role))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('student_dashboard'))  # Redirect to the default dashboard or home page
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)


@app.route('/register/form')
def register_form():
    return render_template('register.html')

@app.route('/student/dashboard')
def student_dashboard():
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'student':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch all scores and details
        cursor.execute('SELECT Subjects.SubjectName, Scores.Score, Scores.DateTaken FROM Scores JOIN Subjects ON Scores.SubjectID = Subjects.SubjectID WHERE Scores.StudentID = %s ORDER BY Scores.DateTaken DESC', (session['id'],))
        scores = cursor.fetchall()

        # Fetch the latest score
        if scores:
            latest_score = scores[0]['Score']  # Assuming the scores are ordered by DateTaken DESC
        else:
            latest_score = 'No recent quiz taken'

        # Calculate the total score
        cursor.execute('SELECT SUM(Score) AS TotalScore FROM Scores WHERE StudentID = %s', (session['id'],))
        total_result = cursor.fetchone()
        total_score = total_result['TotalScore'] if total_result else 'No scores available'

        return render_template('student_dashboard.html', scores=scores, latest_score=latest_score, total_score=total_score)
    else:
        return redirect(url_for('login'))
    
   
@app.route('/student/student_svg_scores')
def student_svg_scores():
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'student':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT Subjects.SubjectName, SUM(Scores.Score) as TotalScore
            FROM Scores
            JOIN Subjects ON Scores.SubjectID = Subjects.SubjectID
            WHERE Scores.StudentID = %s
            GROUP BY Scores.SubjectID, Subjects.SubjectName
            ORDER BY Subjects.SubjectName
        ''', (session['id'],))
        scores = cursor.fetchall()
        svg = generate_svg_with_graph(scores, 400, 300)  # Use predefined SVG width and height or adjust as needed
        return Response(svg, mimetype='image/svg+xml')
    else:
        return redirect(url_for('login'))

def generate_svg_with_graph(scores, svg_width, svg_height):
    import random  # Ensure random is imported here if not globally done
    import math
    if not scores:
        return "<svg></svg>"  # Return an empty SVG if no scores

    total_score = sum(score['TotalScore'] for score in scores)
    if total_score == 0:
        return "<svg></svg>"  # Return an empty SVG if sum of scores is zero

    radius = min(svg_width, svg_height) / 2 - 10
    center_x, center_y = svg_width / 2, svg_height / 2
    start_angle = 0

    svg = ['<svg width="{}" height="{}" xmlns="http://www.w3.org/2000/svg">'.format(svg_width, svg_height)]

    colors = ['red', 'green', 'yellow', 'orange', 'pink', 'cyan', 'magenta', 'lime']  # More colors
    for score in scores:
        # Select a color for the current slice
        fill_color = random.choice(colors)

        # Calculate the angle for each slice
        slice_angle = (score['TotalScore'] / total_score) * 360
        end_angle = start_angle + slice_angle

        # Convert angles to radians for the calculations
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        # Calculate the end points for each slice
        x1 = center_x + radius * math.cos(start_rad)
        y1 = center_y + radius * math.sin(start_rad)
        x2 = center_x + radius * math.cos(end_rad)
        y2 = center_y + radius * math.sin(end_rad)

        # Determine if the slice is more than 180 degrees
        large_arc = 1 if slice_angle > 180 else 0

        # Create the path for the slice
        path_d = f"M {center_x} {center_y} L {x1} {y1} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} z"
        svg.append(f'<path d="{path_d}" fill="{fill_color}"/>')
        
        # Calculate label positioning
        label_angle_rad = math.radians(start_angle + slice_angle / 2)
        label_x = center_x + (radius / 1.5) * math.cos(label_angle_rad)
        label_y = center_y + (radius / 1.5) * math.sin(label_angle_rad)
        
        # Text visibility: Use white or black based on slice color
        text_fill = 'black' if fill_color in ['blue', 'green', 'purple', 'red', 'cyan'] else 'blue'
    
        # Add label for the slice, increased font size to 16 and stroke-width to 0.3
        svg.append(f'<text x="{label_x}" y="{label_y}" font-size="19" text-anchor="middle" fill="{text_fill}" stroke="black" stroke-width="0.3">'
                   f'{score["SubjectName"]} ({100 * score["TotalScore"] / total_score:.1f}%)</text>')
        
        start_angle = end_angle

    svg.append('</svg>')
    return "".join(svg)





@app.route('/take_quiz', methods=['GET', 'POST'])
def take_quiz():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'student':
        subjects = cursor.execute('SELECT * FROM Subjects')
        subjects = cursor.fetchall()

        if request.method == 'POST':
            selected_subject = request.form['subject']
            cursor.execute('SELECT * FROM Questions WHERE SubjectID = %s', (selected_subject,))
            questions = cursor.fetchall()
            return render_template('take_quiz.html', subjects=subjects, questions=questions, selected_subject=selected_subject)
        else:
            return render_template('take_quiz.html', subjects=subjects)
    else:
        return redirect(url_for('login'))

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'student':
        answers = {}
        for key, value in request.form.items():
            if key.startswith('answer'):
                question_id = key.replace('answer', '')
                answers[question_id] = value

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT QuestionID, CorrectOption, SubjectID FROM Questions WHERE QuestionID IN %s', (tuple(answers.keys()),))
        correct_answers = cursor.fetchall()

        score = 0
        for question in correct_answers:
            question_id = str(question['QuestionID'])
            if answers.get(question_id) == question['CorrectOption']:
                score += 1
        
        # Insert the score into the Scores table
        cursor.execute('INSERT INTO Scores (StudentID, SubjectID, Score) VALUES (%s, %s, %s)', (session['id'], question['SubjectID'], score))
        mysql.connection.commit()

        # Calculate total score
        cursor.execute('SELECT SUM(Score) AS TotalScore FROM Scores WHERE StudentID = %s', (session['id'],))
        total_score = cursor.fetchone()['TotalScore']

        # Redirect to dashboard with scores info
        return redirect(url_for('student_dashboard', latest_score=score, total_score=total_score))
    else:
        return redirect(url_for('login'))

@app.route('/teacher/dashboard', methods=['GET'])
def teacher_dashboard():
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'teacher':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT q.QuestionID, q.SubjectID, q.QuestionText, q.OptionA, q.OptionB, q.OptionC, q.OptionD, q.CorrectOption, s.SubjectName
            FROM questions q
            JOIN subjects s ON q.SubjectID = s.SubjectID
            ORDER BY q.QuestionID DESC
        """)
        questions = cursor.fetchall()
        return render_template('teacher_dashboard.html', questions=questions)
    else:
        return redirect(url_for('login'))


@app.route('/delete_question/<int:question_id>', methods=['GET'])
def delete_question(question_id):
    if 'loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'teacher':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('DELETE FROM Questions WHERE QuestionID = %s', (question_id,))
        mysql.connection.commit()
        flash("Question deleted successfully!")
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('login'))



@app.route('/createquiz', methods=['GET', 'POST'])
def createquiz():
    # Ensure user is logged in and has the teacher role
    if not ('loggedin' in session and session['loggedin'] and 'username' in session and 'Role' in session and session['Role'] == 'teacher'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve data from form
        subject_name = request.form.get('subject')
        question_text = request.form.get('question')
        options = {
            'A': request.form.get('optionA'),
            'B': request.form.get('optionB'),
            'C': request.form.get('optionC'),
            'D': request.form.get('optionD')
        }
        correct_option = request.form.get('correctOption')
# Input validation
        if not all([subject_name, question_text, options['A'], options['B'], options['C'], options['D'], correct_option]):
            flash("All fields are required.", "error")
            return render_template('create_quiz.html')
        
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Get the subject ID based on the subject name
            cursor.execute('SELECT SubjectID FROM Subjects WHERE SubjectName = %s', (subject_name,))
            subject = cursor.fetchone()
            if not subject:
                flash("Subject not found.", "error")
                return render_template('create_quiz.html')

            # Insert the new question into the database
            cursor.execute('''
                INSERT INTO Questions (SubjectID, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (subject['SubjectID'], question_text, options['A'], options['B'], options['C'], options['D'], correct_option))
            mysql.connection.commit()
            
            flash("Quiz created successfully!", "success")
            return redirect(url_for('teacher_dashboard'))  # Redirect to the dashboard after successful creation
        
        except MySQLdb.Error as e:
            mysql.connection.rollback()  # Rollback transaction on error
            flash(f"Database error: {e}", "error")
            return render_template('create_quiz.html')
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {e}", "error")
            return render_template('create_quiz.html')

    # If it's not a POST request, render the form
    return render_template('create_quiz.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'loggedin' in session and session['loggedin'] and 'username' in session and session['Role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            if 'search_term' in request.form:
                search_term = request.form['search_term']
                cursor.execute("SELECT * FROM Users WHERE Username LIKE %s OR Email LIKE %s", (f"%{search_term}%", f"%{search_term}%"))
            elif 'update_role' in request.form:
                user_id = request.form['user_id']
                new_role = request.form['new_role']
                cursor.execute("UPDATE Users SET Role = %s WHERE UserID = %s", (new_role, user_id))
                mysql.connection.commit()
                flash(f"Role updated successfully for user ID {user_id} to {new_role}.", 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            cursor.execute('SELECT UserID, Username, Email, Role FROM Users')
        users = cursor.fetchall()
        return render_template('admin_dashboard.html', users=users)
    else:
        flash('You must be logged in as an admin to view this page.', 'error')
        return redirect(url_for('login'))


    

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'loggedin' in session and session['loggedin'] and 'username' in session and session['Role'] == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('DELETE FROM Users WHERE UserID = %s', (user_id,))
        mysql.connection.commit()
        flash('User successfully deleted.', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized attempt to delete user.', 'error')
        return redirect(url_for('login'))
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
