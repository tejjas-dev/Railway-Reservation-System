import os
import psycopg2
import psycopg2.extras
import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Railway Reservation System")

# Serve static files (CSS) and HTML templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ----------------------------------------------------------
# DB Connection helper
# ----------------------------------------------------------
def get_db():
    """Returns a psycopg2 connection using DATABASE_URL env variable."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set!")
    conn = psycopg2.connect(db_url)
    return conn


# ----------------------------------------------------------
# Page Routes (serve HTML)
# ----------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def passenger_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


# ----------------------------------------------------------
# API: Get all trains
# ----------------------------------------------------------
@app.get("/api/trains")
def get_trains():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Raw SQL - fetch all trains ordered by train number
    cur.execute("""
        SELECT train_id, train_number, train_name, source, destination,
               departure_time::text, arrival_time::text, available_seats, fare
        FROM Trains
        ORDER BY train_number
    """)
    trains = cur.fetchall()
    cur.close()
    conn.close()
    return list(trains)


# ----------------------------------------------------------
# API: Book a ticket (INSERT Passenger if new, then INSERT Ticket)
# ----------------------------------------------------------
@app.post("/api/book")
async def book_ticket(request: Request):
    data = await request.json()

    full_name    = data.get("full_name", "").strip()
    email        = data.get("email", "").strip()
    phone        = data.get("phone", "").strip()
    age          = data.get("age")
    train_id     = data.get("train_id")
    journey_date = data.get("journey_date")

    if not all([full_name, email, phone, age, train_id, journey_date]):
        raise HTTPException(status_code=400, detail="All fields are required.")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Check seat availability before booking
        cur.execute("SELECT available_seats FROM Trains WHERE train_id = %s", (train_id,))
        train = cur.fetchone()
        if not train:
            raise HTTPException(status_code=404, detail="Train not found.")
        if train["available_seats"] <= 0:
            raise HTTPException(status_code=400, detail="No seats available on this train.")

        # Upsert passenger: insert if email doesn't exist, else get existing ID
        cur.execute("""
            INSERT INTO Passengers (full_name, email, phone, age)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE
                SET full_name = EXCLUDED.full_name,
                    phone     = EXCLUDED.phone,
                    age       = EXCLUDED.age
            RETURNING passenger_id
        """, (full_name, email, phone, age))
        passenger_id = cur.fetchone()["passenger_id"]

        # Assign next available seat number for this train + date combo
        cur.execute("""
            SELECT COALESCE(MAX(seat_number), 0) + 1 AS next_seat
            FROM Tickets
            WHERE train_id = %s AND journey_date = %s
        """, (train_id, journey_date))
        seat_number = cur.fetchone()["next_seat"]

        # Insert ticket - the TRIGGER will auto-decrease available_seats
        cur.execute("""
            INSERT INTO Tickets (passenger_id, train_id, journey_date, seat_number, status)
            VALUES (%s, %s, %s, %s, 'Confirmed')
            RETURNING ticket_id
        """, (passenger_id, train_id, journey_date, seat_number))
        ticket_id = cur.fetchone()["ticket_id"]

        conn.commit()
        print(f"[BOOKING] Ticket #{ticket_id} booked for passenger {email} on train {train_id}")
        return {"message": "Ticket booked successfully!", "ticket_id": ticket_id}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Booking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------
# API: Get bookings by email (uses the VIEW)
# ----------------------------------------------------------
@app.get("/api/bookings")
def get_bookings(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Query the VIEW we created in schema.sql
    cur.execute("""
        SELECT ticket_id, train_number, train_name, source, destination,
               departure_time, arrival_time, journey_date::text,
               seat_number, status, fare, booked_at::text
        FROM booking_summary
        WHERE passenger_email = %s
        ORDER BY booked_at DESC
    """, (email,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return list(bookings)


# ----------------------------------------------------------
# API: Admin - Add a new train
# ----------------------------------------------------------
@app.post("/api/admin/trains")
async def add_train(request: Request):
    data = await request.json()

    train_number   = data.get("train_number", "").strip()
    train_name     = data.get("train_name", "").strip()
    source         = data.get("source", "").strip()
    destination    = data.get("destination", "").strip()
    departure_time = data.get("departure_time")
    arrival_time   = data.get("arrival_time")
    total_seats    = data.get("total_seats")
    fare           = data.get("fare")

    if not all([train_number, train_name, source, destination, departure_time, arrival_time, total_seats, fare]):
        raise HTTPException(status_code=400, detail="All fields are required.")

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Trains (train_number, train_name, source, destination,
                                departure_time, arrival_time, total_seats, available_seats, fare)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (train_number, train_name, source, destination,
              departure_time, arrival_time, total_seats, total_seats, fare))
        conn.commit()
        print(f"[ADMIN] New train added: {train_number} - {train_name}")
        return {"message": f"Train '{train_name}' added successfully!"}

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Train number already exists.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Adding train failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------
# API: Admin - Get all bookings (uses the VIEW)
# ----------------------------------------------------------
@app.get("/api/admin/bookings")
def admin_get_all_bookings():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Full booking summary from the VIEW
    cur.execute("""
        SELECT ticket_id, passenger_name, passenger_email, passenger_phone,
               train_number, train_name, source, destination,
               journey_date::text, seat_number, status, fare, booked_at::text
        FROM booking_summary
        ORDER BY booked_at DESC
    """)
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return list(bookings)


# ----------------------------------------------------------
# API: Admin - Cancel (delete) a ticket
# ----------------------------------------------------------
@app.delete("/api/admin/tickets/{ticket_id}")
def cancel_ticket(ticket_id: int):
    conn = get_db()
    cur = conn.cursor()

    try:
        # Update status to Cancelled - the UPDATE TRIGGER restores seats
        cur.execute("""
            UPDATE Tickets SET status = 'Cancelled'
            WHERE ticket_id = %s AND status = 'Confirmed'
        """, (ticket_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ticket not found or already cancelled.")

        conn.commit()
        print(f"[ADMIN] Ticket #{ticket_id} cancelled")
        return {"message": f"Ticket #{ticket_id} has been cancelled."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Cancel ticket failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------
# Run locally with: python main.py
# ----------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
