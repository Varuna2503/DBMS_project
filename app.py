from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import mysql.connector
import re
import csv
import io
from datetime import datetime

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
    if not phone:
        return False
    # Clean up any accidental leading or trailing spaces
    cleaned_phone = str(phone).strip()
    pattern = r'^\d{10}$'
    return re.match(pattern, cleaned_phone) is not None


def mark_overdue_bills(conn, cursor):
    """Unpaid bills whose due date has passed become Overdue."""
    cursor.execute("UPDATE Maintenance_Bills SET status = 'Overdue' WHERE status = 'Unpaid' AND due_date < CURDATE()")
    conn.commit()


def csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


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


@app.route('/admin/overview')
def admin_overview():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    data = {'residents': 0, 'inside': 0, 'today': 0, 'open_complaints': 0,
            'dues_count': 0, 'dues_total': 0, 'overdue': 0}
    occupancy = {'Owner': 0, 'Tenant': 0, 'Vacant': 0}
    recent_visitors, due_list, open_list = [], [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        mark_overdue_bills(conn, cursor)
        cursor.execute("SELECT occupancy_type, COUNT(*) AS n FROM Flats GROUP BY occupancy_type")
        for row in cursor.fetchall():
            occupancy[row['occupancy_type']] = row['n']

        cursor.execute("SELECT COUNT(*) AS n FROM Residents")
        data['residents'] = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM Visitors WHERE exit_time IS NULL")
        data['inside'] = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM Visitors WHERE DATE(entry_time) = CURDATE()")
        data['today'] = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM Complaints WHERE status = 'Open'")
        data['open_complaints'] = cursor.fetchone()['n']
        cursor.execute("""
            SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total,
                   COALESCE(SUM(status = 'Overdue'), 0) AS overdue
            FROM Maintenance_Bills WHERE status IN ('Unpaid', 'Overdue')
        """)
        row = cursor.fetchone()
        data['dues_count'], data['dues_total'], data['overdue'] = row['n'], row['total'], int(row['overdue'])

        cursor.execute("SELECT * FROM DailyVisitorLogView ORDER BY entry_time DESC LIMIT 5")
        recent_visitors = cursor.fetchall()
        cursor.execute("SELECT * FROM PendingDuesView ORDER BY due_date ASC LIMIT 5")
        due_list = cursor.fetchall()
        cursor.execute("""
            SELECT c.*, f.flat_number, b.block_name
            FROM Complaints c
            JOIN Flats f ON c.flat_id = f.flat_id
            JOIN Blocks b ON f.block_id = b.block_id
            WHERE c.status = 'Open'
            ORDER BY c.created_at DESC LIMIT 5
        """)
        open_list = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('admin_overview.html', data=data, occupancy=occupancy,
                           recent_visitors=recent_visitors, due_list=due_list, open_list=open_list)


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

    # Summary cards, derived from the visitor log
    today = datetime.now().date()
    stats = {'today': 0, 'inside': 0, 'checked_out': 0, 'pending': 0}
    for v in visitor_log:
        if v['entry_time'] and v['entry_time'].date() == today:
            stats['today'] += 1
        if v['exit_time'] is None:
            stats['inside'] += 1
            if not v['is_pre_approved']:
                stats['pending'] += 1
        elif v['exit_time'].date() == today:
            stats['checked_out'] += 1

    return render_template('admin_visitors.html', visitor_log=visitor_log, flats=flats, stats=stats)


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
        mark_overdue_bills(conn, cursor)
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
            "INSERT INTO Visitors (flat_id, visitor_name, phone, vehicle_number, entry_time, is_pre_approved) VALUES (%s, %s, %s, %s, NOW(), %s)",
            (flat_id, visitor_name, phone, vehicle_number, 1 if request.form.get('is_pre_approved') else 0)
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


@app.route('/approve_visitor/<int:visitor_id>', methods=['POST'])
def approve_visitor(visitor_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Visitors SET is_pre_approved = TRUE WHERE visitor_id = %s", (visitor_id,))
        conn.commit()
        flash("Visitor marked as approved.", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('admin_visitors'))


@app.route('/generate_bills', methods=['POST'])
def generate_bills():
    """Bill every occupied flat for a month at a rate per sq ft, skipping flats already billed."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        month = int(request.form['bill_month'])
        year = int(request.form['bill_year'])
        rate = float(request.form['rate'])
        due_date = request.form['due_date']
    except (KeyError, ValueError):
        flash("Enter a valid month, year, rate and due date.", "error")
        return redirect(url_for('admin_bills'))
    if not (1 <= month <= 12) or year < 2024 or rate <= 0:
        flash("Month must be 1-12, year 2024 or later, and the rate above zero.", "error")
        return redirect(url_for('admin_bills'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Maintenance_Bills (flat_id, bill_month, bill_year, amount, due_date, status)
            SELECT f.flat_id, %s, %s, ROUND(f.square_feet * %s, 2), %s, 'Unpaid'
            FROM Flats f
            WHERE f.occupancy_type <> 'Vacant'
              AND NOT EXISTS (SELECT 1 FROM Maintenance_Bills mb
                              WHERE mb.flat_id = f.flat_id AND mb.bill_month = %s AND mb.bill_year = %s)
        """, (month, year, rate, due_date, month, year))
        created = cursor.rowcount
        conn.commit()
        if created:
            flash(f"Generated {created} bill(s) for {month}/{year}.", "success")
        else:
            flash("Every occupied flat already has a bill for that month.", "error")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error while generating bills: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('admin_bills'))


@app.route('/admin/residents')
def admin_residents():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    residents, flats = [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.resident_id, r.name, r.phone, r.email, r.resident_type, r.is_primary_contact,
                   f.flat_number, b.block_name
            FROM Residents r
            JOIN Flats f ON r.flat_id = f.flat_id
            JOIN Blocks b ON f.block_id = b.block_id
            ORDER BY b.block_name, f.flat_number, r.name
        """)
        residents = cursor.fetchall()
        cursor.execute("""
            SELECT f.flat_id, f.flat_number, f.occupancy_type, b.block_name
            FROM Flats f JOIN Blocks b ON f.block_id = b.block_id
            ORDER BY b.block_name, f.flat_number
        """)
        flats = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('admin_residents.html', residents=residents, flats=flats)


@app.route('/add_resident', methods=['POST'])
def add_resident():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    flat_id = request.form['flat_id']
    name = request.form['name'].strip()
    phone = request.form['phone'].strip()
    email = request.form.get('email', '').strip() or None
    resident_type = request.form['resident_type']
    password = request.form.get('password', '').strip() or 'resident123'

    if not name or resident_type not in ('Owner', 'Tenant'):
        flash("Enter the resident's name and choose Owner or Tenant.", "error")
        return redirect(url_for('admin_residents'))
    if not is_valid_phone(phone):
        flash("Invalid phone number format. Please enter exactly 10 digits.", "error")
        return redirect(url_for('admin_residents'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # The first resident of a flat is its primary contact (keeps the dues view to one row per bill)
        cursor.execute("SELECT COUNT(*) FROM Residents WHERE flat_id = %s", (flat_id,))
        is_primary = cursor.fetchone()[0] == 0
        cursor.execute(
            "INSERT INTO Residents (flat_id, name, phone, email, resident_type, is_primary_contact, password) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (flat_id, name, phone, email, resident_type, is_primary, password)
        )
        # A vacant flat becomes occupied
        cursor.execute("UPDATE Flats SET occupancy_type = %s WHERE flat_id = %s AND occupancy_type = 'Vacant'",
                       (resident_type, flat_id))
        conn.commit()
        flash("Resident added successfully!", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        if err.errno == 1062:
            flash("A resident with this phone number or email already exists.", "error")
        else:
            flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('admin_residents'))


@app.route('/admin/export/visitors.csv')
def export_visitors():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT visitor_id, block_name, flat_number, visitor_name, visitor_phone,
                                 vehicle_number, entry_time, exit_time, is_pre_approved
                          FROM DailyVisitorLogView ORDER BY entry_time DESC""")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return csv_response('visitor_log.csv',
                        ['ID', 'Block', 'Flat', 'Visitor', 'Phone', 'Vehicle', 'Entry', 'Exit', 'Pre-approved'], rows)


@app.route('/admin/export/dues.csv')
def export_dues():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        mark_overdue_bills(conn, cursor)
        cursor.execute("""SELECT flat_number, block_name, resident_name, phone, bill_month, bill_year,
                                 amount, due_date, status
                          FROM PendingDuesView ORDER BY due_date""")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return csv_response('pending_dues.csv',
                        ['Flat', 'Block', 'Resident', 'Phone', 'Month', 'Year', 'Amount', 'Due date', 'Status'], rows)


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
        mark_overdue_bills(conn, cursor)
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


@app.route('/resident_approve_visitor/<int:visitor_id>', methods=['POST'])
def resident_approve_visitor(visitor_id):
    if not session.get('resident_logged_in'):
        return redirect(url_for('resident_login'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Only visitors currently inside, and only for this resident's own flat
        cursor.execute(
            "UPDATE Visitors SET is_pre_approved = TRUE WHERE visitor_id = %s AND flat_id = %s AND exit_time IS NULL",
            (visitor_id, session.get('flat_id'))
        )
        conn.commit()
        flash("Visitor approved.", "success")
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f"Database error: {err}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('resident_dashboard'))


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