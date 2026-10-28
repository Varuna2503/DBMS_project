from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
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
    cursor.execute("SELECT * FROM Residents")
    residents = cursor.fetchall()
    cursor.execute("SELECT * FROM Flats")
    flats = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', pending_dues=pending_dues, visitor_log=visitor_log, residents=residents, flats=flats)

@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    flat_id = request.form['flat_id']
    visitor_name = request.form['visitor_name']
    phone = request.form['phone']
    vehicle_number = request.form['vehicle_number']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Visitors (flat_id, visitor_name, phone, vehicle_number) VALUES (%s, %s, %s, %s)",
        (flat_id, visitor_name, phone, vehicle_number)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)