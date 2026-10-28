from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import re

app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'  # Required for sessions and flashing

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="492225114191",  # <-- your MySQL root password
        database="gated_community_db"
    )

def is_valid_phone(phone):
    pattern = r'^\d{10}$'
    return re.match(pattern, phone) is not None


# ==========================================
# ADMIN / RECEPTIONIST ROUTES (SECTIONS)
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('admin_visitors'))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))


@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('admin_visitors'))


@app.route('/admin/visitors')
def admin_visitors():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    visitor_log, flats = [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM DailyVisitorLogView")
        visitor_log = cursor.fetchall()
        cursor.execute("SELECT * FROM Flats")
        flats = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('admin_visitors.html', visitor_log=visitor_log, flats=flats)


@app.route('/admin/bills')
def admin_bills():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    pending_dues, flats = [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM PendingDuesView")
        pending_dues = cursor.fetchall()
        cursor.execute("SELECT * FROM Flats")
        flats = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('admin_bills.html', pending_dues=pending_dues, flats=flats)


@app.route('/admin/complaints')
def admin_complaints():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    complaints, flats = [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, f.flat_number, b.block_name 
            FROM Complaints c 
            JOIN Flats f ON c.flat_id = f.flat_id 
            JOIN Blocks b ON f.block_id = b.block_id 
            ORDER BY c.created_at DESC
        """)
        complaints = cursor.fetchall()
        cursor.execute("SELECT * FROM Flats")
        flats = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('admin_complaints.html', complaints=complaints, flats=flats)


@app.route('/admin_add_complaint', methods=['POST'])
def admin_add_complaint():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    flat_id = request.form['flat_id']
    category = request.form['category']
    description = request.form['description']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Complaints (flat_id, category, description, status) VALUES (%s, %s, %s, 'Open')",
            (flat_id, category, description)
        )
        conn.commit()
        flash("Complaint logged successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_complaints'))


@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    flat_id = request.form['flat_id']
    visitor_name = request.form['visitor_name']
    phone = request.form['phone']
    vehicle_number = request.form['vehicle_number']

    if not is_valid_phone(phone):
        flash("Invalid phone number format. Please enter exactly 10 digits.", "error")
        return redirect(url_for('admin_visitors'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Visitors (flat_id, visitor_name, phone, vehicle_number, entry_time) VALUES (%s, %s, %s, %s, NOW())",
            (flat_id, visitor_name, phone, vehicle_number)
        )
        conn.commit()
        flash("Visitor checked in successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error during check-in: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_visitors'))


@app.route('/checkout_visitor/<int:visitor_id>', methods=['POST'])
def checkout_visitor(visitor_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Visitors SET exit_time = NOW() WHERE visitor_id = %s AND exit_time IS NULL", (visitor_id,))
        conn.commit()
        flash("Visitor checked out successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error during check-out: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_visitors'))


@app.route('/add_bill', methods=['POST'])
def add_bill():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    flat_id = request.form['flat_id']
    bill_month = request.form['bill_month']
    bill_year = request.form['bill_year']
    amount = request.form['amount']
    due_date = request.form['due_date']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Maintenance_Bills (flat_id, bill_month, bill_year, amount, due_date, status) VALUES (%s, %s, %s, %s, %s, 'Unpaid')",
            (flat_id, bill_month, bill_year, amount, due_date)
        )
        conn.commit()
        flash("Maintenance bill added successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error while adding bill: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_bills'))


@app.route('/pay_bill/<int:bill_id>', methods=['POST'])
def pay_bill(bill_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Maintenance_Bills SET status = 'Paid' WHERE bill_id = %s", (bill_id,))
        conn.commit()
        flash("Bill marked as paid successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error while updating bill: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_bills'))


@app.route('/resolve_complaint/<int:complaint_id>', methods=['POST'])
def resolve_complaint(complaint_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Complaints SET status = 'Resolved' WHERE complaint_id = %s", (complaint_id,))
        conn.commit()
        flash("Complaint marked as resolved!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('admin_complaints'))


# ==========================================
# RESIDENT PORTAL ROUTES
# ==========================================

@app.route('/resident_login', methods=['GET', 'POST'])
def resident_login():
    if request.method == 'POST':
        flat_number = request.form['flat_number']
        password = request.form['password']
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT r.*, f.flat_id, f.flat_number, b.block_name 
                FROM Residents r 
                JOIN Flats f ON r.flat_id = f.flat_id 
                JOIN Blocks b ON f.block_id = b.block_id 
                WHERE f.flat_number = %s AND r.password = %s
            """, (flat_number, password))
            resident = cursor.fetchone()
            
            if resident:
                session['resident_logged_in'] = True
                session['flat_id'] = resident['flat_id']
                session['flat_number'] = resident['flat_number']
                session['resident_name'] = resident.get('resident_name') or resident.get('name', 'Resident')
                session['block_name'] = resident['block_name']
                return redirect(url_for('resident_dashboard'))
            else:
                flash("Invalid flat number or password.", "error")
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "error")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    return render_template('resident_login.html')


@app.route('/resident_dashboard')
def resident_dashboard():
    if not session.get('resident_logged_in'):
        return redirect(url_for('resident_login'))

    flat_id = session.get('flat_id')
    bills, visitors, complaints = [], [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Maintenance_Bills WHERE flat_id = %s", (flat_id,))
        bills = cursor.fetchall()
        cursor.execute("SELECT * FROM Visitors WHERE flat_id = %s ORDER BY entry_time DESC", (flat_id,))
        visitors = cursor.fetchall()
        cursor.execute("SELECT * FROM Complaints WHERE flat_id = %s ORDER BY created_at DESC", (flat_id,))
        complaints = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('resident_dashboard.html', bills=bills, visitors=visitors, complaints=complaints)


@app.route('/resident_add_complaint', methods=['POST'])
def resident_add_complaint():
    if not session.get('resident_logged_in'):
        return redirect(url_for('resident_login'))

    flat_id = session.get('flat_id')
    category = request.form['category']
    description = request.form['description']

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Complaints (flat_id, category, description, status) VALUES (%s, %s, %s, 'Open')", (flat_id, category, description))
        conn.commit()
        flash("Complaint submitted successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
    return redirect(url_for('resident_dashboard'))


@app.route('/resident_logout')
def resident_logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('resident_login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)