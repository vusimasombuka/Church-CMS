from app.extensions import db

class Service(db.Model):
    __tablename__ = "services"

    __table_args__ = (
        # FIXED: Added 'branch_id' to make constraint per-branch
        db.UniqueConstraint(
            'name',
            'day_of_week',
            'time',
            'branch_id',  # ADDED: Each branch can have same service times
            name='unique_service_per_branch'  # Renamed for clarity
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", name="fk_service_branch_id"), nullable=False, index=True)
    branch = db.relationship("Branch", backref="services")