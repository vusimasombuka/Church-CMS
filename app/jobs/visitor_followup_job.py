from datetime import date, timedelta
from app.extensions import db
from app.models.sms_log import SMSLog
from app.models.service import Service
from app.models.check_in import CheckIn
from app.models.sms_template import SMSTemplate
from app.models.branch import Branch
from app.services.sms_rotation_service import get_rotated_template
from app.utils.branching import get_all_branches
import logging

logger = logging.getLogger(__name__)

def visitor_followup_job():
    """
    Runs Mondays at 9:00 AM. Sends one follow-up SMS per visitor per week.
    Processes ALL branches explicitly.
    """
    today = date.today()
    
    # Safety check: Only run on Mondays (cron should handle this, but double-check)
    if today.weekday() != 0:
        logger.info("Not Monday, skipping visitor follow-up")
        return
    
    # Check for minimum templates globally
    active_templates_count = SMSTemplate.query.filter_by(
        message_type="visitor_followup",
        active=True
    ).count()
    
    if active_templates_count < 3:
        logger.warning(f'Rotation Warning: "visitor_followup" has only {active_templates_count} active template(s)')
    
    total_sent = 0
    
    # Iterate through every branch explicitly
    for branch in get_all_branches():
        branch_id = branch.id
        logger.info(f"Processing visitor follow-up for branch: {branch.name}")
        
        # Get active services for this branch (for message content)
        services = Service.query.filter_by(
            branch_id=branch_id,
            active=True
        ).all()
        
        if not services:
            logger.info(f"No active services for branch {branch_id}")
            continue
        
        services_text = "; ".join(f"{s.name}: {s.day_of_week} {s.time}" for s in services)
        
        # Find recent check-ins (last 7 days) for this branch only
        recent_checkins = CheckIn.query.filter(
            CheckIn.branch_id == branch_id,
            CheckIn.visitor_id.isnot(None),
            CheckIn.phone.isnot(None),
            CheckIn.created_at >= today - timedelta(days=7)
        ).all()
        
        for checkin in recent_checkins:
            # Prevent duplicate weekly SMS for this visitor (branch-scoped)
            already_sent = SMSLog.query.filter(
                SMSLog.branch_id == branch_id,
                SMSLog.phone == checkin.phone,
                SMSLog.message_type == "visitor_followup",
                SMSLog.created_at >= today - timedelta(days=7)
            ).first()
            
            if already_sent:
                continue
            
            # Template rotation
            template = get_rotated_template(checkin.phone, "visitor_followup")
            if not template:
                continue
            
            message = template.message.replace("{services}", services_text)
            
            sms = SMSLog(
                phone=checkin.phone,
                message=message,
                message_type="visitor_followup",
                related_table="check_in",
                related_id=checkin.id,
                status="pending",
                branch_id=branch_id,
                template_id=template.id
            )
            
            db.session.add(sms)
            total_sent += 1
    
    logger.info(f"Weekly visitor follow-up completed: {total_sent} messages queued")
    db.session.commit()