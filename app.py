from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import re

app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'  # Required for flashing messages

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="492225114191",  # <-- your MySQL root password
        database="gated_community_db"
    )

def is_valid_phone(phone):
    # Validates that the input consists of exactly 10 digits
    pattern = r'^\d{10}$'
    return re.match(pattern, phone) is not None


@app.route('/')
def index():
    pending_dues, visitor_log, flats = [], [], []
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM PendingDuesView")
        pending_dues = cursor.fetchall()

        cursor.execute("SELECT * FROM DailyVisitorLogView")
        visitor_log = cursor.fetchall()

        cursor.execute("SELECT * FROM Flats")
        flats = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template(
        'index.html',
        pending_dues=pending_dues,
        visitor_log=visitor_log,
        flats=flats
    )


@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    flat_id = request.form['flat_id']
    visitor_name = request.form['visitor_name']
    phone = request.form['phone']
    vehicle_number = request.form['vehicle_number']

    # Phone number validation
    if not is_valid_phone(phone):
        flash("Invalid phone number format. Please enter exactly 10 digits.", "error")
        return redirect(url_for('index'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Visitors (flat_id, visitor_name, phone, vehicle_number, entry_time) "
            "VALUES (%s, %s, %s, %s, NOW())",
            (flat_id, visitor_name, phone, vehicle_number)
        )
        conn.commit()
        flash("Visitor checked in successfully!", "success")
    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        flash(f"Database error during check-in: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
    return redirect(url_for('index'))


@app.route('/pay_bill/<int:bill_id>', methods=['POST'])
def pay_bill(bill_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maintenance_Bills SET status = 'Paid' WHERE bill_id = %s",
            (bill_id,)
        )
        conn.commit()
        flash("Bill marked as paid successfully!", "success")
    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        flash(f"Database error while updating bill: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
    return redirect(url_for('index'))


@app.route('/checkout_visitor/<int:visitor_id>', methods=['POST'])
def checkout_visitor(visitor_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Visitors SET exit_time = NOW() WHERE visitor_id = %s AND exit_time IS NULL",
            (visitor_id,)
        )
        conn.commit()
        flash("Visitor checked out successfully!", "success")
    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        flash(f"Database error during check-out: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)