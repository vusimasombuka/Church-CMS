from app.extensions import db
from datetime import date

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    department = db.Column(db.String(100))
    description = db.Column(db.Text)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", name="fk_event_branch_id"), nullable=False, index=True)
    
    # SMS Reminder Configuration
    sms_reminder_enabled = db.Column(db.Boolean, default=False)
    sms_reminder_90 = db.Column(db.Boolean, default=False)
    sms_reminder_60 = db.Column(db.Boolean, default=False)
    sms_reminder_30 = db.Column(db.Boolean, default=False)
    sms_reminder_7 = db.Column(db.Boolean, default=False)
    
    # Track what's been sent (to avoid duplicates)
    reminder_90_sent = db.Column(db.Boolean, default=False)
    reminder_60_sent = db.Column(db.Boolean, default=False)
    reminder_30_sent = db.Column(db.Boolean, default=False)
    reminder_7_sent = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Event {self.title} on {self.event_date}>"