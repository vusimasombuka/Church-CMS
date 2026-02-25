import sqlite3
import os
from app import create_app, db

# Get database path from your config
app = create_app()
db_path = os.path.join(app.root_path, '..', 'instance', 'cms.db')

print(f"Using database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create audience_segments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS audience_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    filter_criteria JSON,
    estimated_count INTEGER DEFAULT 0,
    created_by INTEGER,
    branch_id INTEGER,
    is_system BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
)
""")

# Create mass_messages table  
cursor.execute("""
CREATE TABLE IF NOT EXISTS mass_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    audience_segment_id INTEGER,
    ad_hoc_filters JSON,
    status VARCHAR(20) DEFAULT 'draft',
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    target_branch_id INTEGER,
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_by INTEGER,
    branch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Add column to sms_logs if not exists
cursor.execute("PRAGMA table_info(sms_logs)")
columns = [col[1] for col in cursor.fetchall()]

if 'mass_message_id' not in columns:
    cursor.execute("ALTER TABLE sms_logs ADD COLUMN mass_message_id INTEGER")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_sms_logs_mass_message_id ON sms_logs(mass_message_id)")
    print("✅ Added mass_message_id column")
else:
    print("✓ mass_message_id already exists")

conn.commit()
conn.close()

print("✅ All messaging tables created successfully!")
print("You can now start your app with: python run.py")