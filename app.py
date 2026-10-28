from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="492225114191",  # <-- put your MySQL root password here
        database="gated_community_db"
    )


@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM PendingDuesView")
    pending_dues = cursor.fetchall()

    cursor.execute("SELECT * FROM DailyVisitorLogView")
    visitor_log = cursor.fetchall()

    cursor.execute("SELECT * FROM Flats")
    flats = cursor.fetchall()

    cursor.close()
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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Visitors (flat_id, visitor_name, phone, vehicle_number, entry_time) "
        "VALUES (%s, %s, %s, %s, NOW())",
        (flat_id, visitor_name, phone, vehicle_number)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))


@app.route('/pay_bill/<int:bill_id>', methods=['POST'])
def pay_bill(bill_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Maintenance_Bills SET status = 'Paid' WHERE bill_id = %s",
        (bill_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))


@app.route('/checkout_visitor/<int:visitor_id>', methods=['POST'])
def checkout_visitor(visitor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Visitors SET exit_time = NOW() WHERE visitor_id = %s AND exit_time IS NULL",
        (visitor_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)