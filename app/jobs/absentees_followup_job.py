from datetime import date, timedelta
from app.extensions import db
from app.models.member import Member
from app.models.visitor import Visitor
from app.models.check_in import CheckIn
from app.models.sms_log import SMSLog
from app.models.branch import Branch
from app.services.sms_rotation_service import get_rotated_template
from app.utils.branching import get_all_branches
import logging

logger = logging.getLogger(__name__)

def absentees_followup_job():
    """
    Runs daily at 10:00 AM. Identifies inactive people (14+ days no check-in) 
    and sends follow-up SMS. Stops after 3 SMS per person, with 7-day spacing.
    Processes ALL branches explicitly.
    """
    today = date.today()
    inactivity_cutoff = today - timedelta(days=14)
    total_queued = 0
    
    # Iterate through every branch explicitly
    for branch in get_all_branches():
        branch_id = branch.id
        logger.info(f"Processing absentees for branch: {branch.name}")
        
        # Process Members for this branch only
        members = Member.query.filter(
            Member.branch_id == branch_id,
            Member.phone.isnot(None)
        ).all()
        
        for member in members:
            if process_person(member, "member", today, inactivity_cutoff, branch_id):
                total_queued += 1
        
        # Process Visitors for this branch only
        visitors = Visitor.query.filter(
            Visitor.branch_id == branch_id,
            Visitor.phone.isnot(None)
        ).all()
        
        for visitor in visitors:
            if process_person(visitor, "visitor", today, inactivity_cutoff, branch_id):
                total_queued += 1
    
    logger.info(f"Absentee follow-up completed: {total_queued} SMS queued")
    db.session.commit()

def process_person(person, person_type, today, inactivity_cutoff, branch_id):
    """
    Process individual person for absentee follow-up.
    Returns True if SMS was queued.
    """
    
    if not person.phone:
        return False
    
    # Get last check-in for this person (scoped to their branch)
    last_checkin = CheckIn.query.filter(
        CheckIn.branch_id == branch_id,
        getattr(CheckIn, f"{person_type}_id") == person.id
    ).order_by(CheckIn.check_in_date.desc()).first()
    
    # Must have checked in before AND be inactive for 14 days
    if not last_checkin:
        return False
        
    if last_checkin.check_in_date > inactivity_cutoff:
        return False
    
    # Get previous follow-up SMS for this person in this branch
    previous_sms = SMSLog.query.filter(
        SMSLog.branch_id == branch_id,
        SMSLog.phone == person.phone,
        SMSLog.message_type == "absentees_follow_up"
    ).order_by(SMSLog.created_at.desc()).all()
    
    # Stop permanently after 3 messages
    if len(previous_sms) >= 3:
        return False
    
    # If already sent before, ensure 7 days spacing
    if previous_sms:
        last_sms_date = previous_sms[0].created_at.date()
        if today < last_sms_date + timedelta(days=7):
            return False
    
    # Get template and send
    template = get_rotated_template(person.phone, "absentees_follow_up")
    if not template:
        return False
    
    message = template.message.replace("{name}", person.first_name)
    
    sms = SMSLog(
        phone=person.phone,
        message=message,
        message_type="absentees_follow_up",
        related_table=person_type,
        related_id=person.id,
        status="pending",
        branch_id=branch_id,
        template_id=template.id
    )
    
    db.session.add(sms)
    logger.info(f"Queued absentee SMS for {person.first_name} ({person.phone}) - Branch {branch_id}")
    return True