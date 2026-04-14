-- ============================================================
--  Railway Reservation System - SPPU DBMS Mini Project
--  Run this entire script in Supabase SQL Editor
-- ============================================================

-- Drop tables if they exist (clean slate)
DROP TABLE IF EXISTS Tickets CASCADE;
DROP TABLE IF EXISTS Passengers CASCADE;
DROP TABLE IF EXISTS Trains CASCADE;

-- Drop view and trigger if they exist
DROP VIEW IF EXISTS booking_summary;
DROP FUNCTION IF EXISTS decrease_seats() CASCADE;


-- ============================================================
-- TABLE 1: Trains
-- ============================================================
CREATE TABLE Trains (
    train_id        SERIAL PRIMARY KEY,
    train_number    VARCHAR(10)  NOT NULL UNIQUE,
    train_name      VARCHAR(100) NOT NULL,
    source          VARCHAR(50)  NOT NULL,
    destination     VARCHAR(50)  NOT NULL,
    departure_time  TIME         NOT NULL,
    arrival_time    TIME         NOT NULL,
    total_seats     INT          NOT NULL CHECK (total_seats > 0),
    available_seats INT          NOT NULL CHECK (available_seats >= 0),
    fare            NUMERIC(8,2) NOT NULL CHECK (fare > 0)
);


-- ============================================================
-- TABLE 2: Passengers
-- ============================================================
CREATE TABLE Passengers (
    passenger_id  SERIAL PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    phone         VARCHAR(15)  NOT NULL,
    age           INT          NOT NULL CHECK (age > 0 AND age < 150)
);


-- ============================================================
-- TABLE 3: Tickets
-- ============================================================
CREATE TABLE Tickets (
    ticket_id    SERIAL PRIMARY KEY,
    passenger_id INT  NOT NULL REFERENCES Passengers(passenger_id) ON DELETE CASCADE,
    train_id     INT  NOT NULL REFERENCES Trains(train_id) ON DELETE CASCADE,
    journey_date DATE NOT NULL,
    seat_number  INT,
    status       VARCHAR(20) NOT NULL DEFAULT 'Confirmed' CHECK (status IN ('Confirmed', 'Cancelled', 'Waiting')),
    booked_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- VIEW: booking_summary
-- Joins Tickets + Passengers + Trains for a full summary
-- ============================================================
CREATE VIEW booking_summary AS
SELECT
    t.ticket_id,
    p.full_name      AS passenger_name,
    p.email          AS passenger_email,
    p.phone          AS passenger_phone,
    tr.train_number,
    tr.train_name,
    tr.source,
    tr.destination,
    tr.departure_time,
    tr.arrival_time,
    t.journey_date,
    t.seat_number,
    t.status,
    tr.fare,
    t.booked_at
FROM Tickets t
JOIN Passengers  p  ON t.passenger_id = p.passenger_id
JOIN Trains      tr ON t.train_id     = tr.train_id;


-- ============================================================
-- TRIGGER: Auto-decrease available_seats on new ticket booking
-- ============================================================
CREATE OR REPLACE FUNCTION decrease_seats()
RETURNS TRIGGER AS $$
BEGIN
    -- Only decrease seats when status is 'Confirmed'
    IF NEW.status = 'Confirmed' THEN
        UPDATE Trains
        SET available_seats = available_seats - 1
        WHERE train_id = NEW.train_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_decrease_seats
AFTER INSERT ON Tickets
FOR EACH ROW
EXECUTE FUNCTION decrease_seats();


-- ============================================================
-- TRIGGER: Auto-restore available_seats when ticket is cancelled
-- ============================================================
CREATE OR REPLACE FUNCTION restore_seats()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'Confirmed' AND NEW.status = 'Cancelled' THEN
        UPDATE Trains
        SET available_seats = available_seats + 1
        WHERE train_id = NEW.train_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_restore_seats
AFTER UPDATE ON Tickets
FOR EACH ROW
EXECUTE FUNCTION restore_seats();


-- ============================================================
-- DUMMY DATA: Trains
-- ============================================================
INSERT INTO Trains (train_number, train_name, source, destination, departure_time, arrival_time, total_seats, available_seats, fare)
VALUES
    ('12127', 'Intercity Express',    'Pune',    'Mumbai',       '06:00', '09:30', 100, 100, 250.00),
    ('12028', 'Shatabdi Express',     'Mumbai',  'Pune',         '16:25', '19:55', 120, 120, 310.00),
    ('11301', 'Udyan Express',        'Pune',    'Bengaluru',    '07:15', '22:45', 200, 200, 520.00),
    ('12163', 'Dadar Express',        'Mumbai',  'Chennai',      '23:55', '18:30', 180, 180, 680.00),
    ('22119', 'Tejas Express',        'Mumbai',  'Nagpur',       '05:50', '15:35', 90,  90,  750.00),
    ('11093', 'Mahanagari Express',   'Pune',    'Delhi',        '16:40', '22:15', 250, 250, 1120.00);


-- ============================================================
-- DUMMY DATA: Passengers
-- ============================================================
INSERT INTO Passengers (full_name, email, phone, age)
VALUES
    ('Rahul Sharma',   'rahul.sharma@gmail.com',  '9876543210', 22),
    ('Priya Patil',    'priya.patil@gmail.com',   '9823456789', 19),
    ('Ankit Desai',    'ankit.desai@yahoo.com',   '9012345678', 25),
    ('Sneha Kulkarni', 'sneha.k@hotmail.com',     '8765432109', 21);


-- ============================================================
-- DUMMY DATA: Tickets (triggers will fire here)
-- ============================================================
INSERT INTO Tickets (passenger_id, train_id, journey_date, seat_number, status)
VALUES
    (1, 1, '2025-08-10', 12, 'Confirmed'),
    (2, 1, '2025-08-10', 13, 'Confirmed'),
    (3, 3, '2025-08-15', 45, 'Confirmed'),
    (4, 5, '2025-08-20', 7,  'Confirmed');


-- Quick check
SELECT * FROM booking_summary;
