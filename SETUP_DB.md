# Local PostgreSQL setup

Use this so `db.py`, `view_db.py`, and the agent can read/write transcript analyses.

## 1. Install PostgreSQL (macOS with Homebrew)

```bash
brew install postgresql@16
```

(Or `postgresql` for the latest; `postgresql@14` / `@15` also work.)

## 2. Start the server

```bash
brew services start postgresql@16
```

To confirm it’s running:

```bash
brew services list
# postgresql@16 should be "started"
```

## 3. Create the database and (optional) user

**Option A – Use default Mac user (no password)**

Default user is often your Mac username. Create the DB:

```bash
createdb customer_support
```

Then in `.env` set:

```env
POSTGRES_USER=your_mac_username
POSTGRES_PASSWORD=
```

(Replace `your_mac_username` with the output of `whoami`.)

**Option B – Use `postgres` superuser with a password**

```bash
# Connect as your Mac user (allowed to create DBs)
psql postgres

# In psql:
CREATE USER postgres WITH PASSWORD 'postgres' SUPERUSER;
CREATE DATABASE customer_support OWNER postgres;
\q
```

Then in `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

(If `postgres` user already exists, just set the password and create the DB:

```bash
psql postgres -c "ALTER USER postgres PASSWORD 'postgres';"
createdb -O postgres customer_support
```

)

## 4. Optional: use a single URL in `.env`

Instead of the five `POSTGRES_*` variables you can set:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/customer_support
```

(Adjust user, password, and DB name to match what you created.)

## 5. Test

```bash
python view_db.py
```

You should see `Found 0 row(s)` (or existing rows after running the agent). If you see “Could not connect to the database”, check that the service is started and that `POSTGRES_USER` / `POSTGRES_PASSWORD` match your DB user.
