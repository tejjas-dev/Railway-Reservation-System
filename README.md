# 🚆 Railway Reservation System
**SPPU DBMS Mini Project** | Python + FastAPI + PostgreSQL (Supabase)

---

## Project Structure

```
railway/
├── main.py               ← FastAPI backend (raw SQL with psycopg2)
├── schema.sql            ← DB setup: Tables, VIEW, TRIGGERs, dummy data
├── requirements.txt
├── Dockerfile
├── templates/
│   ├── index.html        ← Passenger booking page
│   └── admin.html        ← Admin panel
└── static/
    └── style.css
```

---

## Step 1: Set Up the Database (Supabase)

1. Go to [supabase.com](https://supabase.com) → create a free project.
2. Open **SQL Editor** in your project dashboard.
3. Paste the entire contents of `schema.sql` and click **Run**.
4. You'll see the tables, VIEW, and TRIGGERs created. Dummy data is also inserted.
5. Go to **Project Settings → Database** and copy the **Connection String (URI)**.
   It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```

---

## Step 2: Run Locally

### Install dependencies
```bash
pip install -r requirements.txt
```

### Set environment variable
**Windows (CMD):**
```cmd
set DATABASE_URL=postgresql://postgres:yourpassword@db.xxxx.supabase.co:5432/postgres
```

**Mac / Linux / Git Bash:**
```bash
export DATABASE_URL="postgresql://postgres:yourpassword@db.xxxx.supabase.co:5432/postgres"
```

### Start the server
```bash
python main.py
```

Open your browser at: [http://localhost:8000](http://localhost:8000)

---

## Step 3: Deploy on Koyeb

1. Push your project to a **GitHub repository**.
2. Go to [koyeb.com](https://koyeb.com) → **Create App** → select GitHub.
3. Set the build method to **Dockerfile**.
4. Add environment variable:
   - **Key:** `DATABASE_URL`
   - **Value:** your Supabase connection string
5. Set the exposed port to **8000**.
6. Deploy! Koyeb will build and host your app.

---

## DBMS Concepts Used

| Concept      | Where Used |
|--------------|------------|
| Primary Key  | All 3 tables (SERIAL PRIMARY KEY) |
| Foreign Key  | Tickets → Passengers, Tickets → Trains |
| VIEW         | `booking_summary` — joins all 3 tables |
| TRIGGER      | `trg_decrease_seats` — fires on INSERT to Tickets |
| TRIGGER      | `trg_restore_seats` — fires on UPDATE (cancellation) |
| Raw SQL      | All queries in main.py via psycopg2 |
| ON CONFLICT  | Upsert passenger on booking |

---

## Pages

| URL      | Page |
|----------|------|
| `/`      | Passenger booking + view personal tickets |
| `/admin` | Add trains, view & cancel all bookings |
