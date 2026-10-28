DROP DATABASE IF EXISTS gated_community_db;
CREATE DATABASE gated_community_db;
USE gated_community_db;

CREATE TABLE Blocks (
    block_id INT AUTO_INCREMENT PRIMARY KEY,
    block_name VARCHAR(50) NOT NULL UNIQUE,
    total_floors INT NOT NULL CHECK (total_floors > 0)
);

CREATE TABLE Flats (
    flat_id INT AUTO_INCREMENT PRIMARY KEY,
    flat_number VARCHAR(10) NOT NULL,
    block_id INT NOT NULL,
    square_feet INT NOT NULL CHECK (square_feet > 0),
    occupancy_type ENUM('Owner', 'Tenant', 'Vacant') DEFAULT 'Vacant',
    FOREIGN KEY (block_id) REFERENCES Blocks(block_id) ON DELETE CASCADE
);

CREATE TABLE Residents (
    resident_id INT AUTO_INCREMENT PRIMARY KEY,
    flat_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    resident_type ENUM('Owner', 'Tenant') NOT NULL,
    is_primary_contact BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (flat_id) REFERENCES Flats(flat_id) ON DELETE CASCADE
);

CREATE TABLE Visitors (
    visitor_id INT AUTO_INCREMENT PRIMARY KEY,
    flat_id INT NOT NULL,
    visitor_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    vehicle_number VARCHAR(20),
    entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    exit_time DATETIME NULL,
    is_pre_approved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (flat_id) REFERENCES Flats(flat_id) ON DELETE CASCADE
);

CREATE TABLE Maintenance_Bills (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    flat_id INT NOT NULL,
    bill_month INT CHECK (bill_month BETWEEN 1 AND 12),
    bill_year INT CHECK (bill_year >= 2024),
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    due_date DATE NOT NULL,
    status ENUM('Unpaid', 'Paid', 'Overdue') DEFAULT 'Unpaid',
    FOREIGN KEY (flat_id) REFERENCES Flats(flat_id) ON DELETE CASCADE
);

INSERT INTO Blocks (block_name, total_floors) VALUES ('Alpha Block', 5), ('Beta Block', 5), ('Gamma Block', 4);

INSERT INTO Flats (flat_number, block_id, square_feet, occupancy_type) VALUES 
('A-101', 1, 1200, 'Owner'),
('A-102', 1, 1500, 'Tenant'),
('A-103', 1, 1200, 'Vacant'),
('B-201', 2, 1800, 'Owner'),
('B-202', 2, 1500, 'Tenant'),
('C-301', 3, 1000, 'Owner'),
('C-302', 3, 1000, 'Vacant');

INSERT INTO Residents (flat_id, name, phone, email, resident_type, is_primary_contact) VALUES 
(1, 'Rajesh Sharma', '9876543210', 'rajesh@gmail.com', 'Owner', TRUE),
(2, 'Amit Verma', '9123456789', 'amit@gmail.com', 'Tenant', TRUE),
(4, 'Priya Iyer', '9988776655', 'priya@gmail.com', 'Owner', TRUE),
(5, 'Suresh Kumar', '9811223344', 'suresh@gmail.com', 'Tenant', TRUE),
(6, 'Ananya Gupta', '9700112233', 'ananya@gmail.com', 'Owner', TRUE);

INSERT INTO Maintenance_Bills (flat_id, bill_month, bill_year, amount, due_date, status) VALUES 
(1, 10, 2026, 3600.00, '2026-10-15', 'Paid'),
(2, 10, 2026, 4500.00, '2026-10-15', 'Unpaid'),
(4, 10, 2026, 5400.00, '2026-10-15', 'Overdue'),
(5, 10, 2026, 4500.00, '2026-10-15', 'Unpaid'),
(6, 10, 2026, 3000.00, '2026-10-15', 'Paid');

CREATE VIEW PendingDuesView AS
SELECT 
    f.flat_number,
    b.block_name,
    r.name AS resident_name,
    r.phone,
    mb.bill_month,
    mb.bill_year,
    mb.amount,
    mb.due_date,
    mb.status
FROM Maintenance_Bills mb
JOIN Flats f ON mb.flat_id = f.flat_id
JOIN Blocks b ON f.block_id = b.block_id
JOIN Residents r ON f.flat_id = r.flat_id
WHERE mb.status IN ('Unpaid', 'Overdue') AND r.is_primary_contact = TRUE;

CREATE VIEW DailyVisitorLogView AS
SELECT 
    v.visitor_id,
    b.block_name,
    f.flat_number,
    v.visitor_name,
    v.phone AS visitor_phone,
    v.vehicle_number,
    v.entry_time,
    v.exit_time,
    v.is_pre_approved
FROM Visitors v
JOIN Flats f ON v.flat_id = f.flat_id
JOIN Blocks b ON f.block_id = b.block_id;