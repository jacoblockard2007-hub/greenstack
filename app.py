import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g

app = Flask(__name__)
DATABASE = '/data/greenstack.db'

READING_ZIPS = {'19601', '19602', '19603', '19604', '19605', '19606',
                '19607', '19608', '19609', '19610', '19611'}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        os.makedirs('/data', exist_ok=True)
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                condition TEXT,
                zip_code TEXT,
                status TEXT DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                difficulty TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        # Seed sample data if empty
        count = db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
        if count == 0:
            db.executemany(
                'INSERT INTO listings (title, description, condition, zip_code, status) VALUES (?,?,?,?,?)',
                [
                    ('Lenovo ThinkPad X390', 'Found this at a yard sale on Muhlenberg St. Powers on, gets to the BIOS screen then freezes. No RAM or SSD in it. Screen looks fine, keyboard is clean. Might just need RAM seated properly — I don\'t have the parts to test it.', 'Incomplete', '19601', 'available'),
                    ('Dell Latitude 5400 (lot of 2)', 'My cousin worked at an office that was shutting down. These two came home with him. Neither has a hard drive. One boots to PXE no problem, the other shows a fan error on startup. Both have 8GB RAM still in them. Free to whoever can use them.', 'Incomplete', '19604', 'available'),
                    ('HP Pavilion 15 — no power', 'My daughter spilled water on this about a year ago. Let it dry out for weeks but it never came back on. The screen has no cracks and the keyboard feels fine. Charging light doesn\'t even flicker. Could be the power board or worse. Comes with the charger.', 'Damaged', '19602', 'available'),
                    ('Dell OptiPlex 7050 Mini', 'Pulled from a small business on Penn Ave that closed. Boots fine, runs, but the SSD has a bad sector and Windows keeps failing to load past the login screen. Could probably just swap the drive. Comes with power brick. No monitor.', 'Broken', '19605', 'available'),
                    ('Acer Chromebook 14 — cracked screen', 'Kid dropped it. Everything works — keyboard, trackpad, wifi, charges fine — but the LCD is cracked bad in the corner and has a dead zone. If someone can source a replacement panel this is basically a free laptop. Comes with charger.', 'Damaged', '19601', 'pending'),
                ]
            )
            db.executemany(
                'INSERT INTO guides (title, category, difficulty, content) VALUES (?,?,?,?)',
                [
                    (
                        'ThinkPad CPU Swap: T-Series Guide',
                        'CPU Upgrade',
                        'Intermediate',
                        '''## Overview
Swapping CPUs on ThinkPad T-series laptops (T430, T440p, T490) is one of the best bang-for-buck upgrades in the reviver community.

## Tools Required
- T5/T8 Torx screwdrivers
- Thermal paste (Noctua NT-H1 recommended)
- Isopropyl alcohol 90%+
- Anti-static mat

## Steps
1. **Power down completely** — remove battery and unplug AC adapter. Hold power for 10s.
2. **Remove bottom panel** — 7x Torx T8 screws. Note the two hidden screws under the RAM door.
3. **Disconnect cooling fan** — unplug the fan header from the board before removing the heatsink.
4. **Remove heatsink** — 4 captive screws in order: 4, 3, 2, 1 (reverse of tightening order).
5. **Swap CPU** — ZIF socket on T440p/T490. Align triangle markers. Never force.
6. **Apply thermal paste** — pea-sized dot center of die. Spread thin with card.
7. **Reassemble** — reverse order. Torque heatsink screws evenly in X-pattern.
8. **POST check** — boot and verify in BIOS before installing OS.

## Compatible CPUs (T440p example)
- i7-4910MQ (35W, best thermal performance)
- i7-4810MQ (drop-in, no BIOS mod needed)

## Notes
BIOS whitelist is NOT present on most T-series. No mod required.'''
                    ),
                    (
                        'Motherboard Audit: Reading for Damage',
                        'Diagnostics',
                        'Advanced',
                        '''## Overview
Before discarding or listing a board, perform a systematic audit. Many "dead" boards are one capacitor away from working.

## Visual Inspection
1. **Blown capacitors** — look for bulging tops or brown crust around base.
2. **Burn marks** — check VRM area near CPU socket and around GPU.
3. **Corrosion** — white/green residue near battery header = liquid damage.
4. **Cold solder joints** — under strong light, look for dull/cracked joints around BGA chips.

## Power-On Audit (No CPU)
- Connect PSU and short PWR_SW pins
- Should get fan spin + POST beeps (if no RAM/CPU)
- No response = likely dead VRM or shorted rail

## Multimeter Checks
- **12V rail**: Should read 11.8–12.2V at main ATX connector
- **5V standby**: Should read 5V with PSU plugged in (not powered on)
- **Continuity**: Check fuse near 24-pin connector — common failure point

## Tools
- Digital multimeter (auto-ranging)
- Magnifying glass / loupe 10x
- Cotton swabs + IPA for cleaning corrosion

## When to List vs Trash
- Dead VRM with no burn = listable (repairable)
- Multiple shorted rails = parts only
- GPU BGA reflow possible = listable with note'''
                    ),
                ]
            )
            db.commit()

@app.route('/')
def index():
    db = get_db()
    zip_filter = request.args.get('zip', '').strip()
    search = request.args.get('q', '').strip()

    query = 'SELECT * FROM listings WHERE 1=1'
    params = []

    if zip_filter:
        if zip_filter in READING_ZIPS:
            query += ' AND zip_code = ?'
            params.append(zip_filter)
        else:
            zip_filter = '__invalid__'

    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    query += ' ORDER BY created_at DESC'
    listings = db.execute(query, params).fetchall()
    guides = db.execute('SELECT id, title, category, difficulty FROM guides ORDER BY created_at DESC').fetchall()

    stats = {
        'available': db.execute("SELECT COUNT(*) FROM listings WHERE status='available'").fetchone()[0],
        'pending': db.execute("SELECT COUNT(*) FROM listings WHERE status='pending'").fetchone()[0],
        'guides': db.execute("SELECT COUNT(*) FROM guides").fetchone()[0],
    }

    return render_template('index.html',
                           listings=listings,
                           guides=guides,
                           zip_filter=zip_filter,
                           search=search,
                           stats=stats,
                           reading_zips=sorted(READING_ZIPS))

@app.route('/claim/<int:item_id>', methods=['POST'])
def claim(item_id):
    db = get_db()
    db.execute("UPDATE listings SET status='pending' WHERE id=? AND status='available'", (item_id,))
    db.commit()
    return redirect(url_for('index'))

@app.route('/list', methods=['GET', 'POST'])
def list_item():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        condition = request.form.get('condition', '').strip()
        zip_code = request.form.get('zip_code', '').strip()

        errors = []
        if not title:
            errors.append('Title is required.')
        if zip_code not in READING_ZIPS:
            errors.append(f'ZIP code must be in the Reading, PA area.')

        if not errors:
            db = get_db()
            db.execute(
                'INSERT INTO listings (title, description, condition, zip_code) VALUES (?,?,?,?)',
                (title, description, condition, zip_code)
            )
            db.commit()
            return redirect(url_for('index'))
        return render_template('list_item.html', errors=errors, reading_zips=sorted(READING_ZIPS))

    return render_template('list_item.html', reading_zips=sorted(READING_ZIPS))

@app.route('/guide/<int:guide_id>')
def guide(guide_id):
    db = get_db()
    g_item = db.execute('SELECT * FROM guides WHERE id=?', (guide_id,)).fetchone()
    if not g_item:
        return redirect(url_for('index'))
    return render_template('guide.html', guide=g_item)

@app.route('/guide/new', methods=['GET', 'POST'])
def new_guide():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        difficulty = request.form.get('difficulty', '').strip()
        content = request.form.get('content', '').strip()

        if title and content:
            db = get_db()
            db.execute(
                'INSERT INTO guides (title, category, difficulty, content) VALUES (?,?,?,?)',
                (title, category, difficulty, content)
            )
            db.commit()
            return redirect(url_for('index'))

    return render_template('new_guide.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
