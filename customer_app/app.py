import sqlite3

from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DATABASE = 'customers.db'

# Ensure the database and table exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        # Basic validation
        if not full_name or not email or not phone:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))

        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO customers (full_name, email, phone) VALUES (?, ?, ?)',
                (full_name, email, phone)
            )
            conn.commit()
            conn.close()
            flash('Customer registered successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'error')
        return redirect(url_for('register'))

    return render_template('register.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
