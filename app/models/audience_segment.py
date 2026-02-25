from app.extensions import db
from datetime import datetime

class AudienceSegment(db.Model):
    __tablename__ = "audience_segments"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # JSON filter criteria
    filter_criteria = db.Column(db.JSON, default=dict)
    estimated_count = db.Column(db.Integer, default=0)
    
    # Foreign keys - ensure these match your actual table names
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship("User", backref="audience_segments")
    branch = db.relationship("Branch", backref="audience_segments")
    
    def __repr__(self):
        return f"<AudienceSegment {self.name}>"
    
    def to_dict(self):
        """Serialize segment data"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'filter_criteria': self.filter_criteria,
            'estimated_count': self.estimated_count,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }