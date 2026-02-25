from datetime import datetime, timedelta
from app.extensions import db
from app.models.sms_log import SMSLog
import logging

logger = logging.getLogger(__name__)

def mark_visitor_sms_ready():
    """
    Marks visitor thank-you SMS as ready after 4 hours delay.
    This prevents sending while visitor is still in church.
    
    Status flow:
    - 'scheduled': Waiting for 4-hour delay
    - 'pending': Ready to send (after 4 hours)
    - 'sent': Successfully sent
    """
    four_hours_ago = datetime.utcnow() - timedelta(hours=4)
    
    # Find SMS that are:
    # 1. Type: visitor_thank_you
    # 2. Status: scheduled (waiting for delay)
    # 3. Created 4+ hours ago
    sms_list = SMSLog.query.filter(
        SMSLog.message_type == "visitor_thank_you",
        SMSLog.status == "scheduled",  # Looking for scheduled, not pending
        SMSLog.created_at <= four_hours_ago
    ).all()
    
    if sms_list:
        logger.info(f"Marking {len(sms_list)} visitor SMS as ready to send (4hr delay passed)")
        for sms in sms_list:
            sms.status = "pending"  # Now ready for sender job
        
        db.session.commit()