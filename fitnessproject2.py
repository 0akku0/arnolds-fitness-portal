"""
Arnold's Fitness Management Portal
=====================================
Features:
- Customer registration, login, package purchase, class booking
- Infinite forward calendar generated on-the-fly from trainer schedules
- Admin class planning, trainer management, customer lookup, statistics
- Graphical statistics via matplotlib (saved as PNG charts)
- Historical data seeded from November 2025 for realistic 6-month statistics
- All data persisted in JSON files
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS  [PERSON A]
# ─────────────────────────────────────────────────────────────────────────────
# NEW CONCEPT: import statements
# These load extra Python tools (modules) not available by default.
#   json        → read/write .json files (our database)
#   os          → file paths and folder creation
#   random      → pick random items, generate random numbers
#   hashlib     → scramble passwords so we never store the real text
#   calendar    → renamed cal_module to avoid name clash with our variable "calendar"
#   platform    → detect which OS (Windows/Mac/Linux) we are running on
#   subprocess  → run external commands (used to open chart image files)
#   datetime    → date, datetime, timedelta tools for working with dates and times
# ─────────────────────────────────────────────────────────────────────────────
import json
import os
import random
import hashlib
import calendar as cal_module
import platform
import subprocess
from datetime import datetime, timedelta, date

# NEW CONCEPT: try / except at module level — import guard
# matplotlib is an external library for drawing charts.
# If it is NOT installed the try block fails silently and we set MATPLOTLIB_AVAILABLE = False.
# Every chart function checks this flag before running so the program still works without charts.
try:
    import matplotlib
    matplotlib.use("Agg")          # Non-interactive backend: saves to PNG file, no popup window
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# NEW CONCEPT: Enabling ANSI colour codes on Windows
# Windows Command Prompt does not support colour escape codes by default.
# os.system("") is a trick that forces Windows 10+ to enable ANSI processing
# for this terminal session. On Mac/Linux this line does nothing and is harmless.
if platform.system() == "Windows":
    os.system("")


# ─────────────────────────────────────────────────────────────────────────────
# DATA FILE PATHS  [PERSON A]
# ─────────────────────────────────────────────────────────────────────────────
# NEW CONCEPT: os.path.join / os.path.dirname / os.path.abspath / __file__
# __file__ = the path of this Python script.
# os.path.abspath() converts it to an absolute path (full path from root).
# os.path.dirname() strips the filename to get the containing folder.
# os.path.join() glues folder + filename with the correct separator for the OS.
# Result: data files sit in a "data" folder next to this script, on any OS.
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR            = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USERS_FILE          = os.path.join(DATA_DIR, "users.json")
TRAINERS_FILE       = os.path.join(DATA_DIR, "trainers.json")
BOOKINGS_FILE       = os.path.join(DATA_DIR, "bookings.json")
PURCHASES_FILE      = os.path.join(DATA_DIR, "purchases.json")

# NEW FILES added in this version:
# CUSTOM_CLASSES_FILE  → stores one-off classes the admin adds for a specific date
# DELETED_SLOTS_FILE   → stores slot-keys for recurring classes admin deleted on a specific date
CUSTOM_CLASSES_FILE = os.path.join(DATA_DIR, "custom_classes.json")
DELETED_SLOTS_FILE  = os.path.join(DATA_DIR, "deleted_slots.json")

# NEW CONCEPT: os.makedirs with exist_ok=True
# Creates the data/ and data/charts/ folders automatically.
# exist_ok=True means: do NOT crash if the folder already exists.
CHARTS_DIR = os.path.join(DATA_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS  [PERSON A]
# ─────────────────────────────────────────────────────────────────────────────

# NEW CONCEPT: List  [ ]
# Stores multiple values in order. CLASS_TYPES[0] = "Pilates", CLASS_TYPES[2] = "MMA", etc.
CLASS_TYPES = ["Pilates", "Yoga", "MMA", "Boxing", "KPop Fitness"]

# NEW CONCEPT: Dictionary  { key: value }
# Key → value lookup. STUDIOS["Studio 1"] gives 20 (that studio's capacity).
STUDIOS = {
    "Studio 1": 20,
    "Studio 2": 20,
    "Studio 3": 10,
    "Studio 4": 10,
}

# NEW CONCEPT: Nested Dictionary  { key: { key: value } }
# PACKAGES["MMA x 10"]["price"] → 450
PACKAGES = {
    "Pilates x 10":      {"type": "Pilates",      "sessions": 10, "price": 300,  "per_class": 30},
    "Pilates x 30":      {"type": "Pilates",      "sessions": 30, "price": 660,  "per_class": 22},
    "Yoga x 10":         {"type": "Yoga",          "sessions": 10, "price": 300,  "per_class": 30},
    "Yoga x 30":         {"type": "Yoga",          "sessions": 30, "price": 660,  "per_class": 22},
    "MMA x 10":          {"type": "MMA",           "sessions": 10, "price": 450,  "per_class": 45},
    "MMA x 30":          {"type": "MMA",           "sessions": 30, "price": 1050, "per_class": 35},
    "Boxing x 10":       {"type": "Boxing",        "sessions": 10, "price": 450,  "per_class": 45},
    "Boxing x 30":       {"type": "Boxing",        "sessions": 30, "price": 1050, "per_class": 35},
    "KPop Fitness x 10": {"type": "KPop Fitness",  "sessions": 10, "price": 250,  "per_class": 25},
    "KPop Fitness x 30": {"type": "KPop Fitness",  "sessions": 30, "price": 600,  "per_class": 20},
}

# NEW CONCEPT: Dictionary as lookup table — avoids long if/elif chains
CLASS_REVENUE = {
    "Pilates":      22,
    "Yoga":         22,
    "MMA":          35,
    "Boxing":       35,
    "KPop Fitness": 20,
}

STUDIO_COST    = {"Studio 1": 20, "Studio 2": 20, "Studio 3": 12, "Studio 4": 12}
MONTHLY_RENTAL = 17000


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY SCHEDULE TEMPLATE  [PERSON A]
# NEW CONCEPT: This constant defines the REPEATING weekly timetable.
# Instead of storing every class in a file, get_slots_for_date() reads this
# list and generates the correct classes for ANY date — past or future —
# making the calendar effectively infinite.
#
# NEW CONCEPT: List of Tuples  [ (val1, val2, val3, ...), ... ]
# Each row is a tuple: (weekday 0=Mon…6=Sun, studio, start_time, class_type, trainer_name)
# Tuples use ( ) and cannot be modified after creation, which makes them safe as constants.
# ─────────────────────────────────────────────────────────────────────────────
WEEKLY_SCHEDULE = [
    # ── Monday (0) ──────────────────────────────────────────────────────────
    (0, "Studio 3", "08:00", "MMA",          "John Wick"),
    (0, "Studio 4", "08:00", "Boxing",        "Rocky Tan"),
    (0, "Studio 1", "09:00", "Pilates",       "Linda Lee"),
    (0, "Studio 2", "09:00", "Yoga",          "Indira Raj"),
    (0, "Studio 1", "11:00", "Yoga",          "Linda Lee"),
    (0, "Studio 2", "11:00", "Yoga",          "Alice Booker"),
    (0, "Studio 1", "15:00", "MMA",           "Dean Richards"),
    (0, "Studio 3", "15:00", "Yoga",          "Indira Raj"),
    (0, "Studio 1", "17:00", "KPop Fitness",  "Janice Chew"),
    (0, "Studio 4", "17:00", "Boxing",        "Rocky Tan"),
    (0, "Studio 1", "18:00", "KPop Fitness",  "Janice Chew"),
    (0, "Studio 3", "19:00", "Pilates",       "Ray Vargas"),
    (0, "Studio 2", "19:00", "KPop Fitness",  "Vincent Koh"),
    (0, "Studio 1", "19:30", "MMA",           "Dean Richards"),
    (0, "Studio 3", "19:30", "Boxing",        "John Wick"),
    # ── Tuesday (1) ─────────────────────────────────────────────────────────
    (1, "Studio 3", "08:00", "MMA",           "John Wick"),
    (1, "Studio 1", "08:00", "Pilates",       "Indira Raj"),
    (1, "Studio 2", "09:00", "Yoga",          "Linda Lee"),
    (1, "Studio 2", "11:00", "Yoga",          "Alice Booker"),
    (1, "Studio 4", "17:00", "Boxing",        "Rocky Tan"),
    (1, "Studio 1", "17:00", "KPop Fitness",  "Janice Chew"),
    (1, "Studio 1", "18:00", "KPop Fitness",  "Janice Chew"),
    (1, "Studio 2", "19:00", "KPop Fitness",  "Vincent Koh"),
    (1, "Studio 3", "19:00", "Pilates",       "Ray Vargas"),
    # ── Wednesday (2) ───────────────────────────────────────────────────────
    (2, "Studio 3", "08:00", "MMA",           "John Wick"),
    (2, "Studio 1", "09:00", "Pilates",       "Linda Lee"),
    (2, "Studio 2", "09:00", "Yoga",          "Indira Raj"),
    (2, "Studio 1", "11:00", "Yoga",          "Alice Booker"),
    (2, "Studio 2", "15:00", "Yoga",          "Indira Raj"),
    (2, "Studio 1", "17:00", "KPop Fitness",  "Janice Chew"),
    (2, "Studio 1", "18:00", "KPop Fitness",  "Janice Chew"),
    (2, "Studio 2", "19:00", "KPop Fitness",  "Vincent Koh"),
    (2, "Studio 1", "19:30", "MMA",           "Dean Richards"),
    (2, "Studio 3", "19:30", "Boxing",        "John Wick"),
    # ── Thursday (3) ────────────────────────────────────────────────────────
    (3, "Studio 1", "09:00", "Pilates",       "Linda Lee"),
    (3, "Studio 2", "09:00", "Yoga",          "Indira Raj"),
    (3, "Studio 1", "11:00", "Yoga",          "Alice Booker"),
    (3, "Studio 2", "15:00", "MMA",           "Dean Richards"),
    (3, "Studio 1", "17:00", "KPop Fitness",  "Janice Chew"),
    (3, "Studio 1", "18:00", "KPop Fitness",  "Janice Chew"),
    (3, "Studio 2", "19:00", "KPop Fitness",  "Vincent Koh"),
    (3, "Studio 3", "19:00", "Pilates",       "Ray Vargas"),
    (3, "Studio 1", "19:30", "MMA",           "Dean Richards"),
    (3, "Studio 3", "19:30", "Boxing",        "John Wick"),
    # ── Friday (4) ──────────────────────────────────────────────────────────
    (4, "Studio 3", "08:00", "MMA",           "John Wick"),
    (4, "Studio 1", "09:00", "Pilates",       "Linda Lee"),
    (4, "Studio 2", "15:00", "MMA",           "Dean Richards"),
    (4, "Studio 4", "17:00", "Boxing",        "Rocky Tan"),
    (4, "Studio 1", "17:00", "KPop Fitness",  "Janice Chew"),
    (4, "Studio 1", "18:00", "KPop Fitness",  "Janice Chew"),
    (4, "Studio 2", "19:00", "KPop Fitness",  "Vincent Koh"),
    (4, "Studio 3", "19:00", "Pilates",       "Ray Vargas"),
    # ── Saturday (5) ────────────────────────────────────────────────────────
    (5, "Studio 3", "09:00", "MMA",           "Rocky Tan"),
    (5, "Studio 1", "10:00", "Pilates",       "Linda Lee"),
    (5, "Studio 2", "10:00", "KPop Fitness",  "Vincent Koh"),
    (5, "Studio 4", "11:00", "MMA",           "Dean Richards"),
    # ── Sunday (6) ──────────────────────────────────────────────────────────
    (6, "Studio 2", "10:00", "Yoga",          "Indira Raj"),
    (6, "Studio 1", "11:00", "Yoga",          "Alice Booker"),
]


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT TRAINERS  [PERSON A]
# NEW CONCEPT: List of Dictionaries — each trainer is a {} inside a list [].
# The nested "schedule" dict maps day abbreviation → list of available start times.
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_TRAINERS = [
    {"name": "John Wick",
     "classes": ["MMA", "Boxing"], "rate": 120,
     "schedule": {"Mon": ["08:00","19:30"], "Tue": ["08:00"], "Wed": ["08:00","19:30"],
                  "Thu": ["19:30"], "Fri": ["08:00"], "Sat": [], "Sun": []}},
    {"name": "Rocky Tan",
     "classes": ["MMA", "Boxing"], "rate": 100,
     "schedule": {"Mon": ["08:00","17:00"], "Tue": ["08:00","17:00"], "Wed": ["17:00"],
                  "Thu": ["08:00"], "Fri": ["17:00"], "Sat": ["09:00"], "Sun": []}},
    {"name": "Linda Lee",
     "classes": ["Pilates", "Yoga"], "rate": 85,
     "schedule": {"Mon": ["09:00","11:00"], "Tue": ["08:00","09:00"], "Wed": ["09:00"],
                  "Thu": ["09:00","11:00"], "Fri": ["09:00"], "Sat": ["10:00"], "Sun": []}},
    {"name": "Indira Raj",
     "classes": ["Yoga"], "rate": 90,
     "schedule": {"Mon": ["09:00","15:00"], "Tue": ["08:00"], "Wed": ["09:00","15:00"],
                  "Thu": ["09:00"], "Fri": ["15:00"], "Sat": [], "Sun": ["10:00"]}},
    {"name": "Vincent Koh",
     "classes": ["KPop Fitness"], "rate": 100,
     "schedule": {"Mon": ["19:00"], "Tue": ["19:00"], "Wed": ["19:00"],
                  "Thu": ["19:00"], "Fri": ["19:00"], "Sat": ["10:00"], "Sun": []}},
    {"name": "Ray Vargas",
     "classes": ["Pilates", "KPop Fitness"], "rate": 90,
     "schedule": {"Mon": ["19:00"], "Tue": ["19:00"], "Wed": [],
                  "Thu": ["19:00"], "Fri": ["19:00"], "Sat": [], "Sun": []}},
    {"name": "Janice Chew",
     "classes": ["KPop Fitness"], "rate": 95,
     "schedule": {"Mon": ["17:00","18:00"], "Tue": ["17:00","18:00"], "Wed": ["17:00","18:00"],
                  "Thu": ["17:00","18:00"], "Fri": ["17:00","18:00"], "Sat": [], "Sun": []}},
    {"name": "Dean Richards",
     "classes": ["MMA"], "rate": 110,
     "schedule": {"Mon": ["15:00","19:30"], "Tue": ["15:00"], "Wed": ["19:30"],
                  "Thu": ["15:00","19:30"], "Fri": ["15:00"], "Sat": ["11:00"], "Sun": []}},
    {"name": "Alice Booker",
     "classes": ["Yoga"], "rate": 88,
     "schedule": {"Mon": ["11:00"], "Tue": ["11:00"], "Wed": ["11:00"],
                  "Thu": ["11:00"], "Fri": ["11:00"], "Sat": [], "Sun": ["11:00"]}},
]


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL COLOUR CODES  [PERSON A]
# NEW CONCEPT: class with class-level constants (no __init__ needed here)
# ANSI escape codes tell the terminal to change text colour.
# Usage: print(CLR.GREEN + "text" + CLR.END)  — prints green text, then resets.
# ─────────────────────────────────────────────────────────────────────────────
class CLR:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    END    = "\033[0m"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS  [PERSON A]
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(password):
    """Return SHA-256 hash of password. We store the hash, never the real password."""
    # NEW CONCEPT: hashlib.sha256 + .encode() + .hexdigest()
    # .encode() converts the string to bytes (sha256 requires bytes, not str).
    # .hexdigest() converts the binary hash result to a readable hex string.
    return hashlib.sha256(password.encode()).hexdigest()


def load_json(filepath, default):
    """Load a JSON file and return its contents. Returns default if file not found."""
    # NEW CONCEPT: "with open(...) as f"
    # Opens a file safely — Python auto-closes it when the block ends, even if an error occurs.
    # json.load(f) converts the JSON text in the file into a Python list or dictionary.
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default


def save_json(filepath, data):
    """Convert data to JSON and write it to filepath."""
    # NEW CONCEPT: json.dump(data, f, indent=2)
    # Converts Python list/dict → nicely indented JSON text and saves it to file.
    # indent=2 makes the file human-readable (not one giant line).
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def get_week_start(d):
    """Return the Monday of the week that contains date d."""
    # NEW CONCEPT: date.weekday() and timedelta subtraction
    # d.weekday() = 0 for Monday, 1 for Tuesday … 6 for Sunday.
    # Subtracting that many days always lands on the Monday of the same week.
    return d - timedelta(days=d.weekday())


def time_str_to_minutes(t):
    """Convert 'HH:MM' string to total minutes since midnight (used for overlap checks)."""
    # NEW CONCEPT: str.split(":") and map(int, ...)
    # "19:30".split(":") → ["19","30"]
    # map(int, ...) converts each string item to an integer.
    # h, m = ... unpacks the two integers into named variables.
    h, m = map(int, t.split(":"))
    return h * 60 + m


def times_overlap(start1, start2):
    """Return True if two 1-hour classes at start1 and start2 would overlap."""
    return abs(time_str_to_minutes(start1) - time_str_to_minutes(start2)) < 60


def fmt_time(t):
    """Format 'HH:MM' as a readable string: '8am', '11am', '7:30pm' etc."""
    # NEW CONCEPT: f-string format code {m:02d}
    # :02d pads the integer m with a leading zero if it is less than 10.
    # Example: m=5 → "05", m=30 → "30".
    h, m = map(int, t.split(":"))
    suffix    = "am" if h < 12 else "pm"
    display_h = h if h <= 12 else h - 12
    if display_h == 0:
        display_h = 12
    return f"{display_h}{suffix}" if m == 0 else f"{display_h}:{m:02d}{suffix}"


def print_separator(char="─", width=60):
    print(char * width)


def print_header(title):
    print_separator("═")
    print(f"  {title}")
    print_separator("═")


def add_one_month(d):
    """Return the date exactly one calendar month after d, handling month-end edge cases."""
    # NEW CONCEPT: calendar.monthrange(year, month)
    # Returns a tuple (weekday_of_1st, total_days_in_month).
    # [1] gives total days — used to clamp the day if the new month is shorter.
    # Example: Jan 31 + 1 month → Feb 28 (Feb has only 28 days, not 31).
    month = d.month + 1
    year  = d.year
    if month > 12:
        month = 1
        year += 1
    max_day = cal_module.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


def open_chart(filepath):
    """Auto-open a saved PNG chart using the OS default image viewer."""
    # NEW CONCEPT: platform.system() and subprocess
    # platform.system() returns "Windows", "Darwin" (Mac), or "Linux".
    # subprocess.call([...]) runs a shell command from inside Python.
    # Each OS uses a different command to open a file with its default app.
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin":
            subprocess.call(["open", filepath])
        else:
            subprocess.call(["xdg-open", filepath])
        print(CLR.CYAN + f"  Chart saved and opened: {filepath}" + CLR.END)
    except Exception:
        print(CLR.YELLOW + f"  Chart saved: {filepath}" + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# DATA INITIALISATION  [PERSON A]
# ─────────────────────────────────────────────────────────────────────────────
def init_data():
    """Create all required data files with empty defaults if they do not exist yet."""
    if not os.path.exists(TRAINERS_FILE):
        save_json(TRAINERS_FILE, DEFAULT_TRAINERS)

    # NEW CONCEPT: Looping over a list of tuples — (filepath, default_value)
    # Python automatically unpacks each pair into two variables: filepath and default.
    for filepath, default in [
        (USERS_FILE,          []),
        (BOOKINGS_FILE,       []),
        (PURCHASES_FILE,      []),
        (CUSTOM_CLASSES_FILE, []),
        (DELETED_SLOTS_FILE,  []),
    ]:
        if not os.path.exists(filepath):
            save_json(filepath, default)


# ─────────────────────────────────────────────────────────────────────────────
# HISTORICAL DATA SEEDING  [PERSON A]
# NEW: Seeds from 1 November 2025 — exactly 6 months of history.
# Creates 300 fake customers with purchase records spread across the full 6 months,
# and fills each class slot at 50–90% capacity for realistic profit figures.
# Seeded users start with packages: {} (empty) — they must purchase new packages.
# ─────────────────────────────────────────────────────────────────────────────
def seed_historical_data():
    """Seed 6 months of historical data. Skips if already done."""
    bookings = load_json(BOOKINGS_FILE, [])
    if len(bookings) >= 1500:
        return   # Already seeded — do nothing

    print("  [First run: generating 8 months of historical data from Sep 2025...]")

    users     = load_json(USERS_FILE,     [])
    purchases = load_json(PURCHASES_FILE, [])

    # NEW CONCEPT: Set comprehension  { expression for item in iterable }
    # Collects all existing usernames into a set (no duplicates).
    # "if uname in set" is much faster than "if uname in list" for large data.
    existing_names = {u["username"] for u in users}

    first_names = ["Alex","Sam","Jamie","Taylor","Jordan","Morgan","Casey","Riley","Drew","Avery",
                   "Blake","Cameron","Dakota","Elliot","Frankie","Gray","Harper","Indigo","Jesse",
                   "Kennedy","Lena","Marcus","Nina","Owen","Priya","Quinn","Rachel","Sean","Tara","Uma"]
    last_names  = ["Tan","Lee","Lim","Ng","Wong","Chen","Ong","Koh","Chua","Teo",
                   "Goh","Yeo","Ang","Sim","Lam","Ho","Foo","Wee","Yap","Phua"]

    new_users = []
    for i in range(520):          # Generate 520 so we always clear 500 after duplicate checks
        # NEW CONCEPT: random.choice(list) — picks one random item from the list
        uname = f"{random.choice(first_names)}{random.choice(last_names)}{i}"
        if uname in existing_names:
            continue
        new_users.append({
            "username": uname,
            "password": hash_password("password123"),
            "email":    f"{uname}@email.com",
            "age":      random.randint(16, 55),
            "gender":   random.choice(["Male", "Female"]),
            "packages": {}        # Empty — all historical sessions already used
        })
        # NEW CONCEPT: set.add() — adds one value; silently ignores duplicates
        existing_names.add(uname)
        if len(new_users) == 500:
            break

    # NEW CONCEPT: list.extend() — appends every item from new_users into users at once
    users.extend(new_users)
    save_json(USERS_FILE, users)

    all_usernames = [u["username"] for u in users]

    # ── Seed purchase history ────────────────────────────────────────────────
    # NEW CONCEPT: list(dict.items()) — converts PACKAGES into a list of (name, info) pairs
    pkg_list      = list(PACKAGES.items())
    today         = date.today()
    seed_start    = date(2025, 9, 1)     # September 1 2025 = start of our 8-month history
    booking_id    = max((b.get("id", 0) for b in bookings),  default=0) + 1
    purchase_id   = max((p.get("id", 0) for p in purchases), default=0) + 1
    new_purchases = []

    # NEW CONCEPT: (today - seed_start).days
    # Subtracting two date objects gives a timedelta. .days converts it to an integer.
    # This is the total number of days in our seeding window (Nov 2025 → today).
    # We use it to spread purchases EVENLY across the full 6 months so that
    # "Last 4 Weeks", "Last 3 Months", and "Last 12 Months" all have package data.
    seed_total_days = (today - seed_start).days

    for user in new_users:
        # NEW CONCEPT: random.randint(a, b) — random integer between a and b inclusive
        for _ in range(random.randint(1, 3)):
            pkg_name, pkg_info = random.choice(pkg_list)
            # Spread purchases randomly across the FULL 6-month seeding window
            # so every time-period filter (4 weeks, 3 months, 12 months) has data
            p_date = seed_start + timedelta(days=random.randint(0, seed_total_days - 1))
            new_purchases.append({
                "id":       purchase_id,
                "username": user["username"],
                "package":  pkg_name,
                "type":     pkg_info["type"],
                "sessions": pkg_info["sessions"],
                "price":    pkg_info["price"],
                # NEW CONCEPT: date.isoformat() → converts date object to "YYYY-MM-DD" string
                "date":     p_date.isoformat(),
            })
            purchase_id += 1

    # ── Seed booking history ─────────────────────────────────────────────────
    # Walk every day from Nov 1 2025 to yesterday and create booking records.
    new_bookings = []
    cur = seed_start
    while cur < today:
        # NEW CONCEPT: date.weekday() → 0=Mon … 6=Sun
        wday     = cur.weekday()
        date_str = cur.isoformat()

        # NEW CONCEPT: List comprehension with filter
        # Keeps only rows from WEEKLY_SCHEDULE that match today's weekday.
        day_slots = [row for row in WEEKLY_SCHEDULE if row[0] == wday]

        for (_, studio, start, ctype, trainer) in day_slots:
            # Unique key identifying this specific class on this specific date
            sk = f"{date_str}|{ctype}|{start}|{trainer}|{studio}"

            capacity = STUDIOS[studio]
            # NEW CONCEPT: int() truncates a float to an integer
            # Fill each class between 50% and 90% of capacity — realistic studio attendance.
            # This ensures revenue comfortably covers rental, electricity, and trainer costs.
            # Example: Studio 1 (cap 20) → randint(10, 18) students per class.
            fill = random.randint(int(capacity * 0.5), int(capacity * 0.9))

            # NEW CONCEPT: random.sample(population, k)
            # Returns k UNIQUE randomly chosen items from population (no repetition).
            chosen = random.sample(all_usernames, min(fill, len(all_usernames)))

            for uname in chosen:
                new_bookings.append({
                    "id":       booking_id,
                    "username": uname,
                    "slot_key": sk,
                    "date":     date_str,
                    "type":     ctype,
                    "studio":   studio,
                    "start":    start,
                    "trainer":  trainer,
                    "booked_on": (cur - timedelta(days=random.randint(0, 5))).isoformat(),
                })
                booking_id += 1

        cur += timedelta(days=1)

    bookings.extend(new_bookings)
    purchases.extend(new_purchases)
    save_json(BOOKINGS_FILE,  bookings)
    save_json(PURCHASES_FILE, purchases)
    print(f"  [Done: {len(new_users)} users, {len(new_bookings)} bookings seeded from Sep 2025]\n")


# ─────────────────────────────────────────────────────────────────────────────
# ON-THE-FLY SCHEDULE GENERATION  [PERSON A / PERSON C]
# NEW CONCEPT: Instead of pre-storing every class in a file, this function
# generates the correct timetable for ANY date by reading WEEKLY_SCHEDULE.
# It also applies admin overrides (custom additions and deleted slots).
# The calendar works for 2025, 2026, 2027, and beyond — no end date.
# ─────────────────────────────────────────────────────────────────────────────
def get_slots_for_date(target_date):
    """
    Return a sorted list of class slot dicts for target_date.
    Sources:  WEEKLY_SCHEDULE (recurring) + custom_classes.json (admin additions)
    Minus:    deleted_slots.json (admin deletions for specific dates)
    Each slot dict includes booked_count and booked_users pulled from bookings.json.
    """
    date_str = target_date.isoformat()
    wday     = target_date.weekday()    # 0=Mon … 6=Sun

    # Load supporting data once (avoid repeated file reads inside the loop)
    deleted_keys = load_json(DELETED_SLOTS_FILE,  [])
    custom_list  = load_json(CUSTOM_CLASSES_FILE, [])
    bookings     = load_json(BOOKINGS_FILE,        [])

    # NEW CONCEPT: Building two count dictionaries from bookings in ONE loop pass
    # booking_counts[sk] = how many students booked that slot
    # booking_users[sk]  = list of usernames who booked that slot
    booking_counts = {}
    booking_users  = {}
    for b in bookings:
        sk = b.get("slot_key", "")
        if not sk:
            continue
        booking_counts[sk] = booking_counts.get(sk, 0) + 1
        # NEW CONCEPT: dict.setdefault(key, default)
        # Returns the value for key if it exists; otherwise inserts key with default and returns it.
        # Used to initialise an empty list before the first append.
        booking_users.setdefault(sk, []).append(b["username"])

    slots = []

    # ── Step 1: Recurring template slots ────────────────────────────────────
    for (d, studio, start, ctype, trainer) in WEEKLY_SCHEDULE:
        if d != wday:
            continue
        sk = f"{date_str}|{ctype}|{start}|{trainer}|{studio}"
        if sk in deleted_keys:
            continue    # Admin deleted this slot for this specific date only
        end_h    = int(start.split(":")[0]) + 1
        end_time = f"{end_h:02d}:{start.split(':')[1]}"
        slots.append({
            "slot_key":     sk,
            "date":         date_str,
            "studio":       studio,
            "start":        start,
            "end":          end_time,
            "type":         ctype,
            "trainer":      trainer,
            "capacity":     STUDIOS[studio],
            "booked_count": booking_counts.get(sk, 0),
            "booked_users": booking_users.get(sk, []),
            "is_custom":    False,
        })

    # ── Step 2: Admin-added one-off custom classes ───────────────────────────
    for c in custom_list:
        if c["date"] != date_str:
            continue
        sk = f"custom_{c['id']}"
        slots.append({
            "slot_key":     sk,
            "date":         date_str,
            "studio":       c["studio"],
            "start":        c["start"],
            "end":          c["end"],
            "type":         c["type"],
            "trainer":      c["trainer"],
            "capacity":     STUDIOS[c["studio"]],
            "booked_count": booking_counts.get(sk, 0),
            "booked_users": booking_users.get(sk, []),
            "is_custom":    True,
        })

    # NEW CONCEPT: sorted() with key=lambda
    # Sorts by start time string (e.g. "08:00" < "17:00" < "19:30").
    return sorted(slots, key=lambda x: x["start"])


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER FUNCTIONS  [PERSON B]
# ─────────────────────────────────────────────────────────────────────────────

def customer_register():
    """Register a new customer account with full input validation."""
    print_header("Customer Registration")
    users = load_json(USERS_FILE, [])

    # NEW CONCEPT: Set comprehension — fast unique-username check
    usernames = {u["username"] for u in users}

    while True:
        # NEW CONCEPT: str.strip() — removes leading/trailing spaces from the typed input
        username = input("  Enter username (no spaces): ").strip()
        if not username or " " in username:
            print(CLR.RED + "  Username cannot be empty or contain spaces." + CLR.END)
            continue
        if username in usernames:
            print(CLR.RED + "  That username is already taken. Please choose another." + CLR.END)
        else:
            break

    password = input("  Enter password (min 6 characters): ").strip()
    if len(password) < 6:
        print(CLR.RED + "  Password too short. Minimum 6 characters required." + CLR.END)
        return

    email = input("  Enter email address: ").strip()
    # NEW CONCEPT: str.count() — counts how many times "@" appears in the string
    # A valid email must have exactly one "@" and at least one "." after it.
    if email.count("@") != 1 or "." not in email.split("@")[1]:
        print(CLR.RED + "  Invalid email. Example: name@example.com" + CLR.END)
        return

    while True:
        # NEW CONCEPT: try / except ValueError
        # int(input(...)) raises ValueError if user types letters instead of numbers.
        # We catch it and show a friendly message, then the while loop asks again.
        try:
            age = int(input("  Enter age: "))
            if age < 16 or age > 120:
                raise ValueError
            break
        except ValueError:
            print(CLR.RED + "  Please enter a valid age (16–120)." + CLR.END)

    gender = ""
    while gender not in ["Male", "Female", "Other"]:
        # NEW CONCEPT: str.capitalize() — first letter uppercase, rest lowercase
        # Handles inputs like "MALE", "male", "mALe" → all become "Male"
        gender = input("  Gender (Male/Female/Other): ").strip().capitalize()

    users.append({
        "username": username,
        "password": hash_password(password),
        "email":    email,
        "age":      age,
        "gender":   gender,
        "packages": {}
    })
    save_json(USERS_FILE, users)
    print(CLR.GREEN + f"\n  Account created! Welcome to Arnold's Fitness, {username}!" + CLR.END)


def customer_login():
    """Prompt for username and password. Return username if valid, else None."""
    print_header("Customer Login")
    users    = load_json(USERS_FILE, [])
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()
    for user in users:
        if user["username"] == username and user["password"] == hash_password(password):
            print(CLR.GREEN + f"\n  Welcome back, {username}!" + CLR.END)
            return username
    print(CLR.RED + "  Invalid username or password." + CLR.END)
    # NEW CONCEPT: returning None — caller checks: if username: ...
    # None is treated as False in an if statement.
    return None


def get_user(username):
    """Return the dict for username, or None if not found."""
    for u in load_json(USERS_FILE, []):
        if u["username"] == username:
            return u
    return None


def update_user(updated_user):
    """Replace the matching user record in users.json with the updated version."""
    users = load_json(USERS_FILE, [])
    # NEW CONCEPT: enumerate(iterable) — yields (index, item) pairs
    # We need the index so we can write users[i] = updated_user.
    for i, u in enumerate(users):
        if u["username"] == updated_user["username"]:
            users[i] = updated_user
            break
    save_json(USERS_FILE, users)


def customer_buy_package(username):
    """Display the package catalogue and process a purchase."""
    print_header("Buy Package")
    # NEW CONCEPT: list(dict.items()) → list of (key, value) tuples we can index by number
    pkg_list = list(PACKAGES.items())
    # NEW CONCEPT: enumerate(iterable, start=1) — numbers items from 1 instead of 0
    # (name, info) — tuple unpacking: each item is a (pkg_name, pkg_dict) pair
    for i, (name, info) in enumerate(pkg_list, 1):
        print(f"  {i:2}. {name:<25} ${info['price']:>5}  (${info['per_class']}/class)")

    choice = input("\n  Enter package number (0 to go back): ").strip()
    if choice == "0":
        return
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(pkg_list):
            raise ValueError
    except ValueError:
        print(CLR.RED + "  Invalid choice." + CLR.END)
        return

    pkg_name, pkg_info = pkg_list[idx]
    # NEW CONCEPT: str.lower() — converts to lowercase so "Y" and "y" both match "y"
    confirm = input(f"\n  Confirm purchase of '{pkg_name}' for ${pkg_info['price']}? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Purchase cancelled.")
        return

    user = get_user(username)
    if pkg_name not in user["packages"]:
        user["packages"][pkg_name] = 0
    user["packages"][pkg_name] += pkg_info["sessions"]
    update_user(user)

    purchases = load_json(PURCHASES_FILE, [])
    # NEW CONCEPT: Generator expression inside max()
    # Loops through purchases and returns the highest "id" value.
    # default=0 prevents a crash when purchases is an empty list.
    new_id = max((p.get("id", 0) for p in purchases), default=0) + 1
    purchases.append({
        "id":       new_id,
        "username": username,
        "package":  pkg_name,
        "type":     pkg_info["type"],
        "sessions": pkg_info["sessions"],
        "price":    pkg_info["price"],
        # NEW CONCEPT: date.today().isoformat() → today's date as "YYYY-MM-DD" string
        "date":     date.today().isoformat(),
    })
    save_json(PURCHASES_FILE, purchases)
    sessions_now = user["packages"][pkg_name]
    print(CLR.GREEN + f"\n  '{pkg_name}' added! You now have {sessions_now} sessions remaining." + CLR.END)


def customer_view_packages(username):
    """Show all active packages and remaining session counts for this customer."""
    print_header("Your Active Packages")
    user = get_user(username)
    # NEW CONCEPT: Dictionary comprehension with condition
    # {k: v for k, v in dict.items() if v > 0} — keeps only packages with sessions left
    pkgs = {k: v for k, v in user.get("packages", {}).items() if v > 0}
    if not pkgs:
        print("  You have no active packages.")
        print("  → Select 'Buy package' from the menu to get started.")
    else:
        for name, sessions in pkgs.items():
            bar = "▓" * min(sessions, 30)   # Visual bar capped at 30 blocks
            print(f"  {name:<25} {sessions:>3} sessions  {bar}")
    input("\n  Press Enter to continue...")


# ─────────────────────────────────────────────────────────────────────────────
# CLASS BOOKING  [PERSON C]
# COMPLETELY REWRITTEN to use get_slots_for_date() (on-the-fly generation).
# Booking window: today to exactly 1 calendar month ahead (add_one_month()).
# Calendar is infinite — navigates forward forever through any year.
# ─────────────────────────────────────────────────────────────────────────────
def customer_register_class(username):
    """Browse the class calendar week by week and register for a class."""
    today              = date.today()
    max_book_date      = add_one_month(today)       # 1 calendar month ahead
    current_week_start = get_week_start(today)
    max_week_start     = get_week_start(max_book_date)

    # NEW CONCEPT: date arithmetic to compute max navigable weeks
    # (max_week_start - current_week_start).days → number of days between two Mondays
    # Dividing by 7 gives the number of full weeks we can navigate forward.
    max_offset = (max_week_start - current_week_start).days // 7
    week_offset = 0    # 0 = current week

    while True:
        # NEW CONCEPT: timedelta(weeks=N) — shift the date forward by N weeks
        week_start = current_week_start + timedelta(weeks=week_offset)
        week_end   = week_start + timedelta(days=6)

        # NEW CONCEPT: date.strftime() inside an f-string
        # "%d %b %Y" formats as "05 May 2026"
        print_header(f"Class Schedule  [{week_start.strftime('%d %b %Y')} – {week_end.strftime('%d %b %Y')}]")
        print(f"  Bookings open: today → {max_book_date.strftime('%d %b %Y')} (1 month ahead)\n")

        # Build (day, slot) list for every class this week that hasn't passed
        week_slots = []
        for d_offset in range(7):
            day = week_start + timedelta(days=d_offset)
            # NEW CONCEPT: Calling get_slots_for_date() — the on-the-fly generator
            for slot in get_slots_for_date(day):
                if day < today:
                    continue    # Skip past days entirely
                if day == today:
                    # NEW CONCEPT: datetime.combine + datetime.strptime
                    # Merges a date and a time string into a full datetime object
                    # so we can compare it with datetime.now().
                    cls_dt = datetime.combine(
                        day, datetime.strptime(slot["start"], "%H:%M").time()
                    )
                    if cls_dt <= datetime.now():
                        continue    # Class already started today
                week_slots.append((day, slot))

        if not week_slots:
            print("  No upcoming classes this week.")
        else:
            current_day = None
            for idx, (day, slot) in enumerate(week_slots, 1):
                if day != current_day:
                    current_day = day
                    print(CLR.CYAN + f"\n  {day.strftime('%A  (%d %b %Y)')}" + CLR.END)

                slots_left = slot["capacity"] - slot["booked_count"]
                already    = username in slot["booked_users"]
                # NEW CONCEPT: Ternary inline expression — value_if_true if condition else value_if_false
                status_tag = (CLR.GREEN  + " [BOOKED]" + CLR.END) if already else \
                             (CLR.RED    + " [FULL]"   + CLR.END) if slots_left == 0 else ""
                slot_txt = f"{slots_left} slot{'s' if slots_left != 1 else ''} left"
                custom_tag = " *custom*" if slot["is_custom"] else ""
                print(f"  {idx:3}. {slot['type']:<16} {fmt_time(slot['start'])}-{fmt_time(slot['end'])}"
                      f"  {slot['trainer']:<16}  {slot['studio']:<9}  {slot_txt}{status_tag}{custom_tag}")

        # Build navigation bar
        nav = []
        if week_offset < max_offset:
            nav.append("[N] Next week")
        if week_offset > 0:
            nav.append("[P] Previous week")
        nav.append("[0] Back")
        print("\n  " + "   ".join(nav))

        # NEW CONCEPT: str.upper() — so "n" and "N" both match the check "== 'N'"
        choice = input("\n  Enter class number or N/P/0: ").strip().upper()

        if choice == "0":
            return
        elif choice == "N":
            if week_offset < max_offset:
                week_offset += 1
            else:
                print(CLR.YELLOW + f"  Cannot book past {max_book_date.strftime('%d %b %Y')} (1-month limit)." + CLR.END)
        elif choice == "P":
            if week_offset > 0:
                week_offset -= 1
            else:
                print(CLR.YELLOW + "  Already at the current week." + CLR.END)
        else:
            # NEW CONCEPT: try / except for number input
            try:
                num = int(choice)
                if num < 1 or num > len(week_slots):
                    raise ValueError
                day, slot = week_slots[num - 1]

                # ── Validation before confirming ─────────────────────────────
                if day > max_book_date:
                    print(CLR.RED + "  That date is outside the 1-month booking window." + CLR.END)
                    continue
                if slot["booked_count"] >= slot["capacity"]:
                    print(CLR.RED + "  This class is full." + CLR.END)
                    continue
                user = get_user(username)
                if username in slot["booked_users"]:
                    print(CLR.RED + "  You are already registered for this class." + CLR.END)
                    continue
                pkg_type = slot["type"]
                # NEW CONCEPT: any() with generator expression
                # Returns True if at least ONE package matches class type AND has sessions left.
                has_pkg = any(
                    PACKAGES[p]["type"] == pkg_type and cnt > 0
                    for p, cnt in user.get("packages", {}).items()
                )
                if not has_pkg:
                    print(CLR.RED + f"  You need an active {pkg_type} package to book this class." + CLR.END)
                    continue

                print(f"\n  Class:   {slot['type']} — {day.strftime('%A, %d %b %Y')}")
                print(f"  Time:    {fmt_time(slot['start'])} – {fmt_time(slot['end'])}")
                print(f"  Trainer: {slot['trainer']}")
                print(f"  Studio:  {slot['studio']}")
                confirm = input("  Confirm booking? (y/n): ").strip().lower()

                if confirm == "y":
                    # Deduct 1 session from the first matching package
                    # NEW CONCEPT: list(dict) — copies keys into a list before looping
                    # This allows safe deletion of a key while the loop is running.
                    for p in list(user["packages"]):
                        if PACKAGES[p]["type"] == pkg_type and user["packages"][p] > 0:
                            user["packages"][p] -= 1
                            if user["packages"][p] == 0:
                                # NEW CONCEPT: del dict[key] — removes key-value pair entirely
                                del user["packages"][p]
                            break
                    update_user(user)

                    # Save booking record
                    bookings = load_json(BOOKINGS_FILE, [])
                    new_id   = max((b.get("id", 0) for b in bookings), default=0) + 1
                    bookings.append({
                        "id":       new_id,
                        "username": username,
                        "slot_key": slot["slot_key"],
                        "date":     day.isoformat(),
                        "type":     slot["type"],
                        "studio":   slot["studio"],
                        "start":    slot["start"],
                        "trainer":  slot["trainer"],
                        "booked_on": date.today().isoformat(),
                    })
                    save_json(BOOKINGS_FILE, bookings)
                    print(CLR.GREEN + "\n  Booking confirmed! 1 session deducted from your package." + CLR.END)
                else:
                    print("  Booking cancelled.")

            except ValueError:
                print(CLR.RED + "  Please enter a valid class number." + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER MENU  [PERSON B]
# Header matches assignment exactly: @@@@Members Main Menu@@@@
# ─────────────────────────────────────────────────────────────────────────────
def customer_menu(username):
    """Main menu loop for a logged-in customer."""
    while True:
        print_header("@@@@Members Main Menu@@@@")
        print("  1. Buy package")
        print("  2. View my packages")
        print("  3. Register for class")
        print("  0. Logout")
        choice = input("\n  Enter option: ").strip()
        if choice == "1":
            customer_buy_package(username)
        elif choice == "2":
            customer_view_packages(username)
        elif choice == "3":
            customer_register_class(username)
        elif choice == "0":
            print("  Logged out. See you next time!")
            return
        else:
            print(CLR.RED + "  Invalid option. Please enter 1, 2, 3 or 0." + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — LOGIN  [PERSON D]
# ─────────────────────────────────────────────────────────────────────────────
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = hash_password("admin123")


def admin_login():
    """Verify admin credentials. Return True on success."""
    print_header("Admin Login")
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()
    if username == ADMIN_USERNAME and hash_password(password) == ADMIN_PASSWORD:
        print(CLR.GREEN + "  Access granted. Welcome, Admin!" + CLR.END)
        return True
    print(CLR.RED + "  Invalid admin credentials." + CLR.END)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — CHECK CUSTOMER INFO  [PERSON D]
# NEW REQUIRED FEATURE: Admin can look up any customer by username and view
# their profile, active packages, and most recent 10 bookings.
# ─────────────────────────────────────────────────────────────────────────────
def admin_check_customer_info():
    """Admin searches for and views a customer full profile. Supports partial-name matches."""
    print_header("Check Customer Info")
    search = input("  Enter username (or part of it) to search (0 to go back): ").strip()
    if search == "0":
        return

    users = load_json(USERS_FILE, [])

    # NEW CONCEPT: List comprehension with str.lower() for case-insensitive partial match
    # This returns ALL users whose username contains the search string, not just exact matches.
    # e.g. search "tan" matches "AlexTan5", "JordanTan2" etc.
    matches = [u for u in users if search.lower() in u["username"].lower()]

    if not matches:
        print(CLR.RED + f"  No customer found matching '{search}'." + CLR.END)
        input("\n  Press Enter to continue...")
        return

    # If more than one match, let admin pick which one
    if len(matches) > 1:
        print(f"\n  Found {len(matches)} matching customer(s):")
        for i, u in enumerate(matches, 1):
            print(f"  {i}. {u['username']}")
        try:
            pick = int(input("  Select number to view (0 to cancel): "))
            if pick == 0:
                return
            user = matches[pick - 1]
        except (ValueError, IndexError):
            print(CLR.RED + "  Invalid selection." + CLR.END)
            return
    else:
        user = matches[0]

    print_separator()
    print(f"  Username  : {user['username']}")
    print(f"  Email     : {user.get('email', 'N/A')}")
    print(f"  Age       : {user.get('age', 'N/A')}")
    print(f"  Gender    : {user.get('gender', 'N/A')}")

    # Active packages
    pkgs = {k: v for k, v in user.get("packages", {}).items() if v > 0}
    print("\n  Active Packages:")
    if pkgs:
        for name, sessions in pkgs.items():
            print(f"    {name:<25} {sessions} sessions remaining")
    else:
        print("    None")

    # Most recent 10 bookings
    bookings = load_json(BOOKINGS_FILE, [])
    # NEW CONCEPT: List comprehension filter + sorted() with reverse=True
    # [b for b in bookings if b["username"] == user["username"]] → only this user's bookings
    # sorted(..., key=lambda x: x["date"], reverse=True) → newest date first
    # [:10] — list slice: take only the first 10 items from the sorted result
    recent = sorted(
        [b for b in bookings if b["username"] == user["username"]],
        key=lambda x: x["date"],
        reverse=True
    )[:10]

    print(f"\n  Recent Bookings (up to 10):")
    if recent:
        for b in recent:
            print(f"    {b['date']}  {b['type']:<16}  {fmt_time(b['start']):<8}  {b['trainer']}")
    else:
        print("    No booking history.")

    total_bookings = sum(1 for b in bookings if b["username"] == user["username"])
    print(f"\n  Total all-time bookings: {total_bookings}")
    input("\n  Press Enter to continue...")


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — CLASS PLANNER  [PERSON D]
# UPDATED: Uses get_slots_for_date() (on-the-fly generation).
# Delete → writes slot_key to deleted_slots.json for that specific date.
# Add    → writes new entry to custom_classes.json.
# ─────────────────────────────────────────────────────────────────────────────
def admin_class_planner():
    """View, add, and delete classes for any date."""
    while True:
        print_header("Class Planner")
        date_str = input("  Enter date (YYYY-MM-DD) or 0 to go back: ").strip()
        if date_str == "0":
            return
        # NEW CONCEPT: try / except with date.fromisoformat()
        # Raises ValueError if the string is not a valid YYYY-MM-DD date.
        try:
            view_date = date.fromisoformat(date_str)
        except ValueError:
            print(CLR.RED + "  Invalid date. Use YYYY-MM-DD format (e.g. 2026-05-10)." + CLR.END)
            continue

        day_slots = get_slots_for_date(view_date)

        print(f"\n  {view_date.strftime('%A, %d %b %Y')}:")
        if not day_slots:
            print("  No classes scheduled.")
        else:
            for i, s in enumerate(day_slots, 1):
                tag = "[custom]" if s["is_custom"] else "[recurring]"
                print(f"  {i}. {s['type']:<16} {fmt_time(s['start'])}-{fmt_time(s['end'])}"
                      f"  {s['trainer']:<16}  {s['studio']:<9}"
                      f"  ({s['booked_count']}/{s['capacity']} booked) {tag}")

        print("\n  [A] Add class   [D] Delete class   [0] Back")
        action = input("  Enter option: ").strip().upper()

        if action == "0":
            return
        elif action == "A":
            admin_add_class(date_str, view_date)
        elif action == "D":
            if not day_slots:
                print(CLR.RED + "  No classes to delete." + CLR.END)
                continue
            try:
                del_num = int(input("  Enter class number to delete: ")) - 1
                if del_num < 0 or del_num >= len(day_slots):
                    raise ValueError
                chosen = day_slots[del_num]
                if chosen["booked_count"] > 0:
                    print(CLR.RED + f"  Cannot delete — {chosen['booked_count']} student(s) already registered." + CLR.END)
                    continue
                confirm = input(f"  Delete {chosen['type']} at {fmt_time(chosen['start'])} on {date_str}? (y/n): ").lower()
                if confirm == "y":
                    if chosen["is_custom"]:
                        # NEW CONCEPT: List comprehension as filter to remove one item
                        # Rebuilds the list without the item whose id matches the custom slot.
                        custom = [c for c in load_json(CUSTOM_CLASSES_FILE, [])
                                  if f"custom_{c['id']}" != chosen["slot_key"]]
                        save_json(CUSTOM_CLASSES_FILE, custom)
                    else:
                        # For recurring slots, add the slot_key to deleted_slots.json
                        deleted = load_json(DELETED_SLOTS_FILE, [])
                        if chosen["slot_key"] not in deleted:
                            deleted.append(chosen["slot_key"])
                        save_json(DELETED_SLOTS_FILE, deleted)
                    print(CLR.GREEN + "  Class deleted." + CLR.END)
            except ValueError:
                print(CLR.RED + "  Invalid input." + CLR.END)


def admin_add_class(date_str, view_date):
    """Add a one-off custom class for a specific date with full validation."""
    trainers = load_json(TRAINERS_FILE, [])
    custom   = load_json(CUSTOM_CLASSES_FILE, [])

    # ── Class type ───────────────────────────────────────────────────────────
    print("\n  Class types:")
    for i, ct in enumerate(CLASS_TYPES, 1):
        print(f"  {i}. {ct}")
    try:
        ct_idx = int(input("  Select class type: ")) - 1
        if ct_idx < 0 or ct_idx >= len(CLASS_TYPES):
            raise ValueError
        class_type = CLASS_TYPES[ct_idx]
    except ValueError:
        print(CLR.RED + "  Invalid choice." + CLR.END)
        return

    # ── Start time ───────────────────────────────────────────────────────────
    time_str = input("  Enter start time (HH:MM, 08:00–20:00, minutes must be 00 or 30): ").strip()
    try:
        # NEW CONCEPT: str.split(":") + map(int,...) → parse HH:MM into two integers
        h, m = map(int, time_str.split(":"))
        if not (8 <= h <= 20) or m not in [0, 30]:
            raise ValueError
        # NEW CONCEPT: f-string zero-padding {h:02d} → 8 becomes "08"
        start_time = f"{h:02d}:{m:02d}"
        end_time   = f"{h+1:02d}:{m:02d}"
        if h + 1 > 21:
            print(CLR.RED + "  Class would end after 9pm — not allowed." + CLR.END)
            return
    except (ValueError, AttributeError):
        print(CLR.RED + "  Invalid time format." + CLR.END)
        return

    # ── Studio ───────────────────────────────────────────────────────────────
    # NEW CONCEPT: list(dict.keys()) → get all studio names as an indexable list
    studio_list = list(STUDIOS.keys())
    print("\n  Studios:")
    for i, s in enumerate(studio_list, 1):
        print(f"  {i}. {s} (capacity {STUDIOS[s]})")
    try:
        st_idx = int(input("  Select studio: ")) - 1
        studio = studio_list[st_idx]
    except (ValueError, IndexError):
        print(CLR.RED + "  Invalid studio." + CLR.END)
        return

    # Check studio conflict against all slots already on this date
    existing = get_slots_for_date(view_date)
    for s in existing:
        if s["studio"] == studio and times_overlap(start_time, s["start"]):
            print(CLR.RED + f"  Conflict: {studio} already has a class at {fmt_time(s['start'])}." + CLR.END)
            return

    # ── Trainer ──────────────────────────────────────────────────────────────
    # NEW CONCEPT: date.strftime("%a") → "Mon", "Tue", "Wed" etc.
    day_abbr = view_date.strftime("%a")
    eligible = []
    for t in trainers:
        if class_type not in t["classes"]:
            continue
        # NEW CONCEPT: dict.get(key, default) → returns [] if day not in schedule
        if start_time not in t["schedule"].get(day_abbr, []):
            continue
        # NEW CONCEPT: any() with generator — True if trainer has any overlapping slot today
        conflict = any(
            s["trainer"] == t["name"] and times_overlap(start_time, s["start"])
            for s in existing
        )
        if not conflict:
            eligible.append(t)

    if not eligible:
        print(CLR.RED + "  No qualified trainers available at this time." + CLR.END)
        return

    print("\n  Available trainers:")
    for i, t in enumerate(eligible, 1):
        print(f"  {i}. {t['name']}  (${t['rate']}/hr)")
    try:
        tr_idx  = int(input("  Select trainer: ")) - 1
        trainer = eligible[tr_idx]
    except (ValueError, IndexError):
        print(CLR.RED + "  Invalid selection." + CLR.END)
        return

    new_id = max((c.get("id", 0) for c in custom), default=0) + 1
    custom.append({"id": new_id, "date": date_str, "studio": studio,
                   "start": start_time, "end": end_time,
                   "type": class_type, "trainer": trainer["name"]})
    save_json(CUSTOM_CLASSES_FILE, custom)
    print(CLR.GREEN + f"  Class added: {class_type} at {fmt_time(start_time)} in {studio} with {trainer['name']}." + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — TRAINER MANAGEMENT  [PERSON D]
# ─────────────────────────────────────────────────────────────────────────────
def admin_view_trainers():
    """List all trainers with options to view/edit schedule or add a new trainer."""
    while True:
        print_header("Trainer Management")
        trainers = load_json(TRAINERS_FILE, [])
        for i, t in enumerate(trainers, 1):
            # NEW CONCEPT: str.join() — joins a list into one string with separator
            # ", ".join(["MMA","Boxing"]) → "MMA, Boxing"
            print(f"  {i:2}. {t['name']:<18}  ({', '.join(t['classes'])})   ${t['rate']}/hr")
        print("\n  Enter number to view schedule, [A] to add trainer, [0] back.")
        choice = input("  Option: ").strip().upper()
        if choice == "0":
            return
        elif choice == "A":
            admin_add_trainer(trainers)
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(trainers):
                    raise ValueError
                admin_view_trainer_schedule(trainers[idx])
            except ValueError:
                print(CLR.RED + "  Invalid input." + CLR.END)


def admin_view_trainer_schedule(trainer):
    """Display a trainer's weekly schedule and optionally update it."""
    print_header(f"Schedule — {trainer['name']}")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day in days:
        # NEW CONCEPT: dict.get(key, default) — safe read; returns [] if key missing
        times = trainer["schedule"].get(day, [])
        # NEW CONCEPT: str.join() with a generator — format each time then join with ", "
        display = ", ".join(fmt_time(t) for t in times) if times else "Not available"
        print(f"  {day}: {display}")

    if input("\n  Edit schedule? (y/n): ").strip().lower() != "y":
        return

    trainers = load_json(TRAINERS_FILE, [])
    for day in days:
        raw = input(f"  {day} times (HH:MM comma-separated, blank = none): ").strip()
        # NEW CONCEPT: Conditional list comprehension
        # If raw is not empty → split by comma, strip spaces, skip blanks.
        # If raw is empty     → store [].
        trainer["schedule"][day] = [t.strip() for t in raw.split(",") if t.strip()] if raw else []

    for i, t in enumerate(trainers):
        if t["name"] == trainer["name"]:
            trainers[i] = trainer
            break
    save_json(TRAINERS_FILE, trainers)
    print(CLR.GREEN + "  Schedule updated." + CLR.END)


def admin_add_trainer(trainers):
    """Collect details for a new trainer and append to trainers.json."""
    name = input("  Full name of new trainer: ").strip()
    # NEW CONCEPT: any() — returns True if ANY existing trainer already has this name
    if not name or any(t["name"] == name for t in trainers):
        print(CLR.RED + "  Name is empty or already exists." + CLR.END)
        return

    print("  Class types available:", ", ".join(CLASS_TYPES))
    raw_classes = input("  Class types this trainer teaches (comma-separated): ").strip()
    # NEW CONCEPT: List comprehension with 'in' filter
    # Only keeps items that are in the CLASS_TYPES list (filters out typos).
    trainer_classes = [c.strip() for c in raw_classes.split(",") if c.strip() in CLASS_TYPES]
    if not trainer_classes:
        print(CLR.RED + "  No valid class types entered." + CLR.END)
        return

    try:
        # NEW CONCEPT: float() — like int() but accepts decimal numbers e.g. 95.50
        rate = float(input("  Hourly rate ($): "))
    except ValueError:
        print(CLR.RED + "  Invalid rate." + CLR.END)
        return

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    schedule = {}
    for day in days:
        raw = input(f"  {day} available times (HH:MM comma-separated, blank = none): ").strip()
        schedule[day] = [t.strip() for t in raw.split(",") if t.strip()] if raw else []

    trainers.append({"name": name, "classes": trainer_classes, "rate": rate, "schedule": schedule})
    save_json(TRAINERS_FILE, trainers)
    print(CLR.GREEN + f"  Trainer '{name}' added successfully." + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — STATISTICS + CHARTS  [PERSON E]
# Each stat function shows text output in the terminal AND saves a PNG chart
# to data/charts/ then auto-opens it with the system image viewer.
# ─────────────────────────────────────────────────────────────────────────────
def admin_statistics():
    """Statistics menu — choose metric and time period."""
    while True:
        print_header("Statistics")
        print("  1. Class registrations by class type")
        print("  2. Packages purchased by class type")
        print("  3. Top 5 trainers by bookings")
        print("  4. Profit report")
        print("  5. Month-over-month registration growth")
        print("  6. Revenue vs cost breakdown by class type")
        print("  7. Most popular time slots")
        print("  0. Back")
        choice = input("\n  Select report: ").strip()
        if choice == "0":
            return
        if choice not in ("1", "2", "3", "4", "5", "6", "7"):
            print(CLR.RED + "  Invalid choice." + CLR.END)
            continue

        # Profit report has an extra tab 4 option (revenue trend line graph)
        if choice == "4":
            print("\n  Time period / view:")
            print("  1. Last 4 weeks")
            print("  2. Last 3 months")
            print("  3. Last 12 months")
            print("  4. Revenue trend line graph (all time)")
            period = input("  Select period / tab: ").strip()
            if period == "4":
                stat_revenue_trend()
                continue
        else:
            print("\n  Time period:")
            print("  1. Last 4 weeks")
            print("  2. Last 3 months")
            print("  3. Last 12 months")
            period = input("  Select period: ").strip()

        today = date.today()
        # NEW CONCEPT: Assigning two variables at once from one expression (tuple unpacking)
        if period == "1":
            cutoff, label = today - timedelta(weeks=4),  "Last 4 Weeks"
        elif period == "2":
            cutoff, label = today - timedelta(days=91),  "Last 3 Months"
        elif period == "3":
            cutoff, label = today - timedelta(days=365), "Last 12 Months"
        else:
            print(CLR.RED + "  Invalid period." + CLR.END)
            continue

        if choice == "1":
            stat_class_registrations(cutoff, label)
        elif choice == "2":
            stat_packages(cutoff, label)
        elif choice == "3":
            stat_top_trainers(cutoff, label)
        elif choice == "4":
            stat_profits(cutoff, label)
        elif choice == "5":
            stat_monthly_growth(cutoff, label)
        elif choice == "6":
            stat_revenue_vs_cost_by_type(cutoff, label)
        elif choice == "7":
            stat_popular_time_slots(cutoff, label)


def stat_class_registrations(cutoff, label):
    """Bookings count per class type — text table + horizontal bar chart PNG."""
    bookings = load_json(BOOKINGS_FILE, [])
    # NEW CONCEPT: Dictionary comprehension — initialise every class type to 0
    counts = {ct: 0 for ct in CLASS_TYPES}
    for b in bookings:
        # NEW CONCEPT: date.fromisoformat() — converts "YYYY-MM-DD" string back to date object
        # We can then compare it with >= cutoff (both are date objects).
        if date.fromisoformat(b["date"]) >= cutoff and b["type"] in counts:
            counts[b["type"]] += 1

    total   = sum(counts.values())
    max_val = max(counts.values(), default=1)

    print_header(f"Class Registrations — {label}")
    # NEW CONCEPT: sorted() with negative lambda → descending order (highest first)
    for ct, count in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * int(count / max_val * 30) if max_val > 0 else ""
        pct = count / total * 100 if total > 0 else 0
        # NEW CONCEPT: f-string {pct:.1f} → float formatted to exactly 1 decimal place
        print(f"  {ct:<18} {count:>5}  {bar}  ({pct:.1f}%)")
    print(f"\n  Total: {total} registrations")

    # ── Matplotlib chart ─────────────────────────────────────────────────────
    # NEW CONCEPT: MATPLOTLIB_AVAILABLE flag — only run if library loaded successfully
    if MATPLOTLIB_AVAILABLE:
        colors = ["#1976D2","#388E3C","#D32F2F","#F57C00","#7B1FA2"]
        types  = list(counts.keys())
        vals   = [counts[t] for t in types]
        fig, ax = plt.subplots(figsize=(9, 5))
        bars    = ax.barh(types, vals, color=colors[:len(types)], edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_width() + max_val * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=10)
        ax.set_xlabel("Number of Registrations")
        ax.set_title(f"Class Registrations by Type\n{label}", fontweight="bold")
        ax.set_xlim(0, max_val * 1.18)
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"registrations_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_packages(cutoff, label):
    """Packages purchased per class type — text table + horizontal bar chart PNG (all 3 periods saved)."""
    purchases = load_json(PURCHASES_FILE, [])
    counts    = {ct: 0 for ct in CLASS_TYPES}
    revenue   = {ct: 0 for ct in CLASS_TYPES}
    for p in purchases:
        if date.fromisoformat(p["date"]) >= cutoff and p["type"] in counts:
            counts[p["type"]]  += 1
            revenue[p["type"]] += p["price"]

    total_pkgs = sum(counts.values())
    max_val    = max(counts.values(), default=1)

    print_header(f"Packages Purchased — {label}")
    # NEW CONCEPT: sorted() descending so highest bar comes first
    for ct, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "\u2588" * int(cnt / max_val * 30) if max_val > 0 else ""
        pct = cnt / total_pkgs * 100 if total_pkgs > 0 else 0
        print(f"  {ct:<18} {cnt:>4} packages  {bar}  ({pct:.1f}%)")
    print(f"\n  Totals:  {total_pkgs} packages   ${sum(revenue.values()):,.2f} revenue")

    if MATPLOTLIB_AVAILABLE:
        colors = ["#1976D2", "#388E3C", "#D32F2F", "#F57C00", "#7B1FA2"]
        types  = list(counts.keys())

        def _draw_package_bar(c_counts, period_label, save_label):
            """Inner helper — draws and saves one bar chart for the given period counts."""
            c_max  = max(c_counts.values(), default=1)
            c_vals = [c_counts[t] for t in types]
            fig2, ax2 = plt.subplots(figsize=(9, 5))
            bars2 = ax2.barh(types, c_vals, color=colors[:len(types)], edgecolor="white")
            for b2, v2 in zip(bars2, c_vals):
                ax2.text(b2.get_width() + c_max * 0.01,
                         b2.get_y() + b2.get_height() / 2,
                         str(v2), va="center", fontsize=10)
            ax2.set_xlabel("Number of Packages Purchased")
            ax2.set_title(f"Packages Purchased by Class Type\n{period_label}", fontweight="bold")
            ax2.set_xlim(0, c_max * 1.18)
            plt.tight_layout()
            p2 = os.path.join(CHARTS_DIR, f"packages_{save_label}.png")
            plt.savefig(p2, dpi=100, bbox_inches="tight")
            plt.close()
            return p2

        # Draw and open the selected period chart
        selected_path = _draw_package_bar(counts, label, label.replace(" ", "_"))
        open_chart(selected_path)

        # NEW CONCEPT: Save all 3 period charts silently so admin can compare them later
        today = date.today()
        extra_periods = [
            (today - timedelta(weeks=4),  "Last 4 Weeks",   "Last_4_Weeks"),
            (today - timedelta(days=91),  "Last 3 Months",  "Last_3_Months"),
            (today - timedelta(days=365), "Last 12 Months", "Last_12_Months"),
        ]
        for ec, el, es in extra_periods:
            if el == label:
                continue    # Already saved above
            ec_counts = {ct: 0 for ct in CLASS_TYPES}
            for p in purchases:
                if date.fromisoformat(p["date"]) >= ec and p["type"] in ec_counts:
                    ec_counts[p["type"]] += 1
            _draw_package_bar(ec_counts, el, es)

        print(CLR.CYAN + f"  All 3 period bar charts saved to {CHARTS_DIR}" + CLR.END)

    input("\n  Press Enter to continue...")


def stat_top_trainers(cutoff, label):
    """Top 5 trainers by booking count — text list + bar chart PNG."""
    bookings = load_json(BOOKINGS_FILE, [])
    # NEW CONCEPT: Building a count dict with dict.get(key, 0) + 1
    # For each booking: read current count (default 0 if unseen), add 1, store back.
    trainer_counts = {}
    for b in bookings:
        if date.fromisoformat(b["date"]) >= cutoff:
            trainer_counts[b["trainer"]] = trainer_counts.get(b["trainer"], 0) + 1

    # NEW CONCEPT: sorted() descending by value, sliced to top 5
    # sorted(..., key=lambda x: -x[1]) → sort by count descending
    # [:5] — list slicing: keeps only the first 5 results
    top5 = sorted(trainer_counts.items(), key=lambda x: -x[1])[:5]

    print_header(f"Top 5 Trainers — {label}")
    medal = ["🥇","🥈","🥉","4.","5."]
    for rank, (name, count) in enumerate(top5):
        print(f"  {medal[rank]}  {name:<20}  {count:>5} bookings")

    if MATPLOTLIB_AVAILABLE:
        names  = [t[0] for t in top5]
        vals   = [t[1] for t in top5]
        colors = ["#FFD700","#C0C0C0","#CD7F32","#1976D2","#388E3C"]
        fig, ax = plt.subplots(figsize=(9, 5))
        bars    = ax.bar(names, vals, color=colors[:len(names)], edgecolor="white")
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(vals) * 0.01,
                    str(val), ha="center", fontsize=10)
        ax.set_ylabel("Total Bookings")
        ax.set_title(f"Top 5 Trainers by Bookings\n{label}", fontweight="bold")
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"top_trainers_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_profits(cutoff, label):
    """
    Profit report — revenue from package sales minus rental, electricity, and trainer fees.
    Revenue  = sum of package purchase prices (from purchases.json) in the period
    Rental   = MONTHLY_RENTAL × distinct calendar months that had classes
    Elec     = STUDIO_COST[studio] per class session
    Trainer  = trainer hourly rate × number of classes they taught (1 hr each)
    """
    # Q3 FIX: Revenue now comes from actual package sales, not per-booking rate.
    # This reflects real gym income: money is earned when a customer buys a package,
    # regardless of how many sessions they actually attend.
    purchases = load_json(PURCHASES_FILE, [])
    bookings  = load_json(BOOKINGS_FILE,  [])
    trainers  = load_json(TRAINERS_FILE,  [])
    trainer_rates = {t["name"]: t["rate"] for t in trainers}

    # Revenue: sum purchase prices within the period
    revenue = sum(
        p["price"]
        for p in purchases
        if date.fromisoformat(p["date"]) >= cutoff
    )

    # Cost: group bookings by slot_key to count distinct class sessions
    slot_groups = {}
    for b in bookings:
        if date.fromisoformat(b["date"]) < cutoff:
            continue
        sk = b.get("slot_key", "")
        if not sk:
            continue
        if sk not in slot_groups:
            slot_groups[sk] = {
                "count": 0, "type": b["type"],
                "studio": b["studio"], "trainer": b["trainer"], "date": b["date"]
            }
        slot_groups[sk]["count"] += 1

    electricity_cost = instructor_cost = 0
    class_months = set()
    for sk, info in slot_groups.items():
        electricity_cost += STUDIO_COST.get(info["studio"], 0)
        instructor_cost  += trainer_rates.get(info["trainer"], 0)
        d = date.fromisoformat(info["date"])
        class_months.add((d.year, d.month))

    rental     = len(class_months) * MONTHLY_RENTAL
    total_cost = rental + electricity_cost + instructor_cost
    profit     = revenue - total_cost

    print_header(f"Profit Report — {label}")
    print(f"  Revenue from package sales:${revenue:>12,.2f}")
    print(f"  Studio rental:            -${rental:>12,.2f}   ({len(class_months)} month(s) × ${MONTHLY_RENTAL:,})")
    print(f"  Electricity/cleaning:     -${electricity_cost:>12,.2f}")
    print(f"  Instructor fees:          -${instructor_cost:>12,.2f}")
    print_separator()
    colour = CLR.GREEN if profit >= 0 else CLR.RED
    print(colour + f"  Net Profit:                ${profit:>12,.2f}" + CLR.END)
    print(f"  Class sessions counted: {len(slot_groups)}")

    if MATPLOTLIB_AVAILABLE:
        categories = ["Revenue", "Rental", "Electricity", "Trainer Fees", "Net Profit"]
        vals       = [revenue, -rental, -electricity_cost, -instructor_cost, profit]
        bar_colors = ["#388E3C" if v >= 0 else "#D32F2F" for v in vals]
        fig, ax    = plt.subplots(figsize=(10, 6))
        bars       = ax.bar(categories, vals, color=bar_colors, edgecolor="white")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel("Amount (SGD $)")
        ax.set_title(f"Profit Breakdown\n{label}", fontweight="bold")
        max_abs = max(abs(v) for v in vals) if vals else 1
        for bar, val in zip(bars, vals):
            ypos = (bar.get_height() if val >= 0 else bar.get_y()) + max_abs * 0.01
            ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                    f"${val:,.0f}", ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"profits_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_revenue_trend():
    """
    Q2: Line graph (Tab 4) — cumulative total revenue from package purchases over all time.
    Each point on the line = running total revenue up to that month.
    Annotations mark key milestones on the curve.
    """
    purchases = load_json(PURCHASES_FILE, [])
    if not purchases:
        print(CLR.RED + "  No purchase data available." + CLR.END)
        input("\n  Press Enter to continue...")
        return

    # Group purchase revenue by calendar month
    # NEW CONCEPT: Building a dict keyed by (year, month) tuple
    monthly = {}
    for p in purchases:
        d = date.fromisoformat(p["date"])
        key = (d.year, d.month)
        monthly[key] = monthly.get(key, 0) + p["price"]

    # Sort months chronologically
    sorted_months = sorted(monthly.keys())

    # Build cumulative revenue list
    # NEW CONCEPT: Accumulating a running total with a simple variable
    running_total = 0
    labels   = []
    cum_vals = []
    for ym in sorted_months:
        running_total += monthly[ym]
        labels.append(f"{ym[0]}-{ym[1]:02d}")
        cum_vals.append(running_total)

    # Text display — ASCII line graph in terminal
    print_header("Revenue Trend — Cumulative Package Revenue (All Time)")

    GRAPH_HEIGHT = 18
    COL_SPACING  = 8
    n            = len(cum_vals)
    GRAPH_WIDTH  = (n - 1) * COL_SPACING + 1

    min_val = 0
    max_val = max(cum_vals) if cum_vals else 1

    def val_to_row(v):
        if max_val == min_val:
            return GRAPH_HEIGHT // 2
        return int((1 - (v - min_val) / (max_val - min_val)) * (GRAPH_HEIGHT - 1))

    point_cols = [i * COL_SPACING for i in range(n)]
    point_rows = [val_to_row(v) for v in cum_vals]

    grid = [[" "] * GRAPH_WIDTH for _ in range(GRAPH_HEIGHT)]

    # Draw connecting line between points first, then place dots on top
    for i in range(n - 1):
        c1, r1 = point_cols[i],     point_rows[i]
        c2, r2 = point_cols[i + 1], point_rows[i + 1]
        dc = c2 - c1
        dr = r2 - r1
        # Step column by column, place exactly ONE character per column
        for step in range(1, dc):
            col        = c1 + step
            interp_row = round(r1 + dr * step / dc)
            if 0 <= interp_row < GRAPH_HEIGHT:
                ch = "╱" if dr < 0 else ("╲" if dr > 0 else "─")
                grid[interp_row][col] = ch

    # Dots on top (overwrite any line character at the dot position)
    for col, row in zip(point_cols, point_rows):
        grid[row][col] = "●"

    y_ticks = {
        0:                        f"${max_val:>10,.0f}",
        GRAPH_HEIGHT // 4:        f"${max_val * 0.75:>10,.0f}",
        GRAPH_HEIGHT // 2:        f"${max_val * 0.50:>10,.0f}",
        (GRAPH_HEIGHT * 3) // 4:  f"${max_val * 0.25:>10,.0f}",
        GRAPH_HEIGHT - 1:         f"${'0':>10}",
    }

    for r in range(GRAPH_HEIGHT):
        y_lbl   = (y_ticks[r] + " |") if r in y_ticks else f"{'':>11}|"
        row_str = ""
        for c in range(GRAPH_WIDTH):
            ch = grid[r][c]
            if ch in ("●", "╱", "╲", "─"):
                row_str += CLR.CYAN + ch + CLR.END
            else:
                row_str += ch
        print(f"  {y_lbl}{row_str}")

    print(f"  {'':>11}+" + "─" * GRAPH_WIDTH)

    label_line = [" "] * GRAPH_WIDTH
    for i, lbl in enumerate(labels):
        col   = point_cols[i]
        start = max(0, col - len(lbl) // 2)
        for j, ch in enumerate(lbl):
            if start + j < GRAPH_WIDTH:
                label_line[start + j] = ch
    print(f"  {'':>12}{''.join(label_line)}")

    print(CLR.GREEN + f"\n  Total revenue to date: ${cum_vals[-1]:,.2f}" + CLR.END)
    print(f"  Months tracked: {len(cum_vals)}   |   Monthly avg: ${sum(monthly.values()) / len(monthly):,.2f}")

    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(labels, cum_vals, color="#1976D2", linewidth=2.5, marker="o", markersize=5)
        ax.fill_between(range(len(labels)), cum_vals, alpha=0.12, color="#1976D2")

        # Rotate x-axis labels so they don't overlap
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Cumulative Revenue (SGD $)")
        ax.set_title("Cumulative Revenue from Package Sales Over Time", fontweight="bold")
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"${x:,.0f}")
        )

        # NEW CONCEPT: Annotations — mark first month, halfway point, and final total
        # ax.annotate() draws a text label with an optional arrow pointing to a data point.
        if len(cum_vals) >= 1:
            ax.annotate(f"Start\n${cum_vals[0]:,.0f}",
                        xy=(0, cum_vals[0]),
                        xytext=(1, cum_vals[0] + cum_vals[-1] * 0.05),
                        fontsize=8, color="#1976D2",
                        arrowprops=dict(arrowstyle="->", color="#1976D2", lw=1.2))
        if len(cum_vals) >= 2:
            mid = len(cum_vals) // 2
            ax.annotate(f"${cum_vals[mid]:,.0f}",
                        xy=(mid, cum_vals[mid]),
                        xytext=(mid + 0.5, cum_vals[mid] + cum_vals[-1] * 0.04),
                        fontsize=8, color="#388E3C",
                        arrowprops=dict(arrowstyle="->", color="#388E3C", lw=1.2))
        if len(cum_vals) >= 1:
            last = len(cum_vals) - 1
            ax.annotate(f"Total\n${cum_vals[last]:,.0f}",
                        xy=(last, cum_vals[last]),
                        xytext=(max(0, last - 2), cum_vals[last] - cum_vals[-1] * 0.08),
                        fontsize=9, fontweight="bold", color="#D32F2F",
                        arrowprops=dict(arrowstyle="->", color="#D32F2F", lw=1.5))

        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, "revenue_trend_all_time.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_monthly_growth(cutoff, label):
    """
    Q5 extra: Month-over-month class registration growth — bar chart showing
    bookings per month with % change annotations between bars.
    """
    bookings = load_json(BOOKINGS_FILE, [])
    monthly  = {}
    for b in bookings:
        if date.fromisoformat(b["date"]) >= cutoff:
            d   = date.fromisoformat(b["date"])
            key = (d.year, d.month)
            monthly[key] = monthly.get(key, 0) + 1

    sorted_months = sorted(monthly.keys())
    if not sorted_months:
        print(CLR.RED + "  No booking data in this period." + CLR.END)
        input("\n  Press Enter to continue...")
        return

    labels = [f"{ym[0]}-{ym[1]:02d}" for ym in sorted_months]
    vals   = [monthly[ym] for ym in sorted_months]

    print_header(f"Month-over-Month Registration Growth — {label}")
    for i, (lbl, val) in enumerate(zip(labels, vals)):
        if i == 0:
            change = ""
        else:
            diff = val - vals[i - 1]
            pct  = diff / vals[i - 1] * 100 if vals[i - 1] > 0 else 0
            arrow = CLR.GREEN + "▲" if diff >= 0 else CLR.RED + "▼"
            change = f"  {arrow} {abs(pct):.1f}%" + CLR.END
        print(f"  {lbl}   {val:>6} bookings{change}")

    if MATPLOTLIB_AVAILABLE:
        colors = ["#388E3C" if (i == 0 or vals[i] >= vals[i-1]) else "#D32F2F"
                  for i in range(len(vals))]
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(labels, vals, color=colors, edgecolor="white")

        # NEW CONCEPT: Annotate % change between adjacent bars
        for i in range(1, len(vals)):
            diff = vals[i] - vals[i - 1]
            pct  = diff / vals[i - 1] * 100 if vals[i - 1] > 0 else 0
            symbol = "▲" if diff >= 0 else "▼"
            col    = "#388E3C" if diff >= 0 else "#D32F2F"
            ypos   = max(vals[i], vals[i - 1]) + max(vals) * 0.02
            ax.annotate(f"{symbol}{abs(pct):.1f}%",
                        xy=((i - 0.5), ypos), ha="center", fontsize=7.5, color=col)

        ax.set_ylabel("Number of Bookings")
        ax.set_title(f"Month-over-Month Class Registrations\n{label}", fontweight="bold")
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"monthly_growth_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_revenue_vs_cost_by_type(cutoff, label):
    """
    Q5 extra: Stacked bar — revenue vs total cost side-by-side per class type.
    Revenue = package purchase revenue for that class type.
    Cost    = electricity + trainer fees for classes of that type.
    """
    purchases = load_json(PURCHASES_FILE, [])
    bookings  = load_json(BOOKINGS_FILE,  [])
    trainers  = load_json(TRAINERS_FILE,  [])
    trainer_rates = {t["name"]: t["rate"] for t in trainers}

    # Revenue by class type from package sales
    rev_by_type  = {ct: 0 for ct in CLASS_TYPES}
    for p in purchases:
        if date.fromisoformat(p["date"]) >= cutoff and p["type"] in rev_by_type:
            rev_by_type[p["type"]] += p["price"]

    # Costs by class type from bookings
    elec_by_type = {ct: 0 for ct in CLASS_TYPES}
    pay_by_type  = {ct: 0 for ct in CLASS_TYPES}
    seen_slots   = set()    # avoid double-counting per distinct class session
    for b in bookings:
        if date.fromisoformat(b["date"]) < cutoff:
            continue
        sk = b.get("slot_key", "")
        if not sk or sk in seen_slots:
            continue
        seen_slots.add(sk)
        ct = b["type"]
        if ct in elec_by_type:
            elec_by_type[ct] += STUDIO_COST.get(b["studio"], 0)
            pay_by_type[ct]  += trainer_rates.get(b["trainer"], 0)

    print_header(f"Revenue vs Costs by Class Type — {label}")
    print(f"  {'Type':<18} {'Revenue':>10} {'Electricity':>12} {'Trainer':>10} {'Net':>10}")
    print_separator()
    for ct in CLASS_TYPES:
        cost = elec_by_type[ct] + pay_by_type[ct]
        net  = rev_by_type[ct] - cost
        col  = CLR.GREEN if net >= 0 else CLR.RED
        print(f"  {ct:<18} ${rev_by_type[ct]:>9,.0f} ${elec_by_type[ct]:>11,.0f}"
              f" ${pay_by_type[ct]:>9,.0f} {col}${net:>9,.0f}{CLR.END}")

    if MATPLOTLIB_AVAILABLE:
        colors_rev  = ["#1976D2", "#388E3C", "#D32F2F", "#F57C00", "#7B1FA2"]
        colors_cost = ["#90CAF9", "#A5D6A7", "#EF9A9A", "#FFCC80", "#CE93D8"]
        x      = range(len(CLASS_TYPES))
        width  = 0.35
        rev_v  = [rev_by_type[ct] for ct in CLASS_TYPES]
        cost_v = [elec_by_type[ct] + pay_by_type[ct] for ct in CLASS_TYPES]

        fig, ax = plt.subplots(figsize=(11, 6))
        bars_r = ax.bar([i - width/2 for i in x], rev_v,  width, label="Revenue",
                        color=colors_rev[0], edgecolor="white")
        bars_c = ax.bar([i + width/2 for i in x], cost_v, width, label="Total Cost",
                        color="#D32F2F", alpha=0.75, edgecolor="white")

        for bar, val in zip(bars_r, rev_v):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(rev_v + cost_v) * 0.01,
                    f"${val:,.0f}", ha="center", fontsize=7.5)
        for bar, val in zip(bars_c, cost_v):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(rev_v + cost_v) * 0.01,
                    f"${val:,.0f}", ha="center", fontsize=7.5)

        ax.set_xticks(list(x))
        ax.set_xticklabels(CLASS_TYPES, fontsize=9)
        ax.set_ylabel("Amount (SGD $)")
        ax.set_title(f"Revenue vs Costs by Class Type\n{label}", fontweight="bold")
        ax.legend()
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"rev_vs_cost_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


def stat_popular_time_slots(cutoff, label):
    """
    Q5 extra: Most popular time slots — counts bookings per start time,
    shows a ranked table and horizontal bar chart.
    """
    bookings = load_json(BOOKINGS_FILE, [])
    slot_counts = {}
    for b in bookings:
        if date.fromisoformat(b["date"]) >= cutoff:
            t = b.get("start", "")
            if t:
                slot_counts[t] = slot_counts.get(t, 0) + 1

    if not slot_counts:
        print(CLR.RED + "  No booking data in this period." + CLR.END)
        input("\n  Press Enter to continue...")
        return

    # Sort by time (not by count) for readable display, then also show top by count
    ranked = sorted(slot_counts.items(), key=lambda x: -x[1])
    max_v  = ranked[0][1]

    print_header(f"Most Popular Time Slots — {label}")
    print(f"  {'Time':<10} {'Bookings':>8}  {'Bar'}")
    print_separator()
    for t, cnt in ranked:
        bar = "█" * int(cnt / max_v * 30)
        print(f"  {fmt_time(t):<10} {cnt:>8}  {bar}")
    print(f"\n  Most popular: {fmt_time(ranked[0][0])} ({ranked[0][1]:,} bookings)")

    if MATPLOTLIB_AVAILABLE:
        times_sorted = sorted(slot_counts.keys())   # chronological order for chart
        t_labels = [fmt_time(t) for t in times_sorted]
        t_vals   = [slot_counts[t] for t in times_sorted]
        colors   = ["#D32F2F" if v == max_v else "#1976D2" for v in t_vals]

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(t_labels, t_vals, color=colors, edgecolor="white")
        for bar, val in zip(bars, t_vals):
            ax.text(bar.get_width() + max_v * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:,}", va="center", fontsize=9)
        ax.set_xlabel("Total Bookings")
        ax.set_title(f"Bookings by Time Slot\n{label}  (Red = most popular)", fontweight="bold")
        ax.set_xlim(0, max_v * 1.18)
        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, f"popular_slots_{label.replace(' ','_')}.png")
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close()
        open_chart(path)

    input("\n  Press Enter to continue...")


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN MENU  [PERSON D]
# Header matches assignment exactly: @@@Admin System@@@
# Option 4 added: Check Customer Info (required feature)
# ─────────────────────────────────────────────────────────────────────────────
def admin_menu():
    """Admin main menu loop."""
    while True:
        print_header("@@@Admin System@@@")
        print("  1. Class planner")
        print("  2. View / Add trainer")
        print("  3. View statistics")
        print("  4. Check customer info")
        print("  0. Logout")
        choice = input("\n  Enter option: ").strip()
        if choice == "1":
            admin_class_planner()
        elif choice == "2":
            admin_view_trainers()
        elif choice == "3":
            admin_statistics()
        elif choice == "4":
            admin_check_customer_info()
        elif choice == "0":
            print("  Admin logged out.")
            return
        else:
            print(CLR.RED + "  Invalid option." + CLR.END)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT  [ALL]
# Header matches assignment exactly: @@@@ Fitness Management Portal @@@@
# NEW CONCEPT: if __name__ == "__main__"
# When this file is run directly (python fitnessproject.py), __name__ == "__main__".
# If another file imported this file, __name__ would be the module name instead.
# This guard ensures main() only runs when we intentionally launch the program.
# ─────────────────────────────────────────────────────────────────────────────
def main():
    init_data()
    seed_historical_data()

    while True:
        print_header("@@@@ Fitness Management Portal @@@@")
        print("  1. Customer Registration / Login")
        print("  2. Admin Login")
        print("  0. Exit")
        choice = input("\n  Enter option: ").strip()

        if choice == "1":
            print("\n  1. Login")
            print("  2. Register new account")
            sub = input("  Enter option: ").strip()
            if sub == "1":
                username = customer_login()
                if username:
                    customer_menu(username)
            elif sub == "2":
                customer_register()
            else:
                print(CLR.RED + "  Invalid option." + CLR.END)

        elif choice == "2":
            if admin_login():
                admin_menu()

        elif choice == "0":
            print("\n  Thank you for using Arnold's Fitness Portal. Goodbye!")
            break
        else:
            print(CLR.RED + "  Invalid option." + CLR.END)


if __name__ == "__main__":
    main()
