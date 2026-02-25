from datetime import date
from app.extensions import db
from app.models.member import Member
from app.models.visitor import Visitor
from app.models.sms_log import SMSLog
from app.models.branch import Branch
from app.services.sms_rotation_service import get_rotated_template
from app.utils.branching import get_all_branches
import logging

logger = logging.getLogger(__name__)

def birthday_sms_job():
    """
    Runs daily at 8:00 AM. Checks ALL branches for birthdays.
    No current_user available in job context - uses explicit branch iteration.
    """
    today = date.today()
    total_queued = 0
    
    # Iterate through every branch explicitly
    for branch in get_all_branches():
        branch_id = branch.id
        logger.info(f"Processing birthdays for branch: {branch.name} (ID: {branch_id})")
        
        # Process Members for this branch only
        members = Member.query.filter(
            Member.branch_id == branch_id,
            Member.date_of_birth.isnot(None),
            Member.phone.isnot(None)
        ).all()
        
        for member in members:
            if process_birthday_person(member, "member", today, branch_id):
                total_queued += 1
        
        # Process Visitors for this branch only
        visitors = Visitor.query.filter(
            Visitor.branch_id == branch_id,
            Visitor.date_of_birth.isnot(None),
            Visitor.phone.isnot(None)
        ).all()
        
        for visitor in visitors:
            if process_birthday_person(visitor, "visitor", today, branch_id):
                total_queued += 1
    
    if total_queued > 0:
        logger.info(f"Birthday SMS job completed: {total_queued} messages queued")
    else:
        logger.info("Birthday SMS job completed: No birthdays today")

def process_birthday_person(person, person_type, today, branch_id):
    """
    Helper function - returns True if SMS was queued.
    Branch-aware to prevent cross-branch SMS.
    """
    
    if not person.phone:
        return False
    
    # Check if today is their birthday
    if (
        person.date_of_birth.month == today.month
        and person.date_of_birth.day == today.day
    ):
        # Check if already sent this year for this branch
        already_sent = SMSLog.query.filter(
            SMSLog.phone == person.phone,
            SMSLog.message_type == "birthday",
            SMSLog.branch_id == branch_id,
            db.extract("year", SMSLog.created_at) == today.year,
        ).first()
        
        if already_sent:
            return False
        
        # Get rotated template
        template = get_rotated_template(person.phone, "birthday")
        if not template:
            logger.warning(f"No birthday template found for {person.phone}")
            return False
        
        message = template.message.replace("{name}", person.first_name)
        
        sms = SMSLog(
            phone=person.phone,
            message=message,
            message_type="birthday",
            related_table=person_type,
            related_id=person.id,
            status="pending",
            branch_id=branch_id,  # Explicit branch assignment
            template_id=template.id
        )
        
        db.session.add(sms)
        return True
    
    return False