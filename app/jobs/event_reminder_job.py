from datetime import date, timedelta
from app.extensions import db
from app.models.event import Event
from app.models.member import Member
from app.models.visitor import Visitor
from app.models.sms_log import SMSLog
from app.models.branch import Branch
from app.services.sms_rotation_service import get_rotated_template
import logging

logger = logging.getLogger(__name__)

def event_reminder_job():
    """
    Sends SMS reminders for upcoming events.
    Runs daily at 8am. Checks for events at 90, 60, 30, 7 days out.
    """
    today = date.today()
    total_queued = 0
    
    # Reminder intervals: (days_before, sent_flag_column, template_type)
    reminders = [
        (90, 'reminder_90_sent', 'event_reminder_90'),
        (60, 'reminder_60_sent', 'event_reminder_60'),
        (30, 'reminder_30_sent', 'event_reminder_30'),
        (7, 'reminder_7_sent', 'event_reminder_7'),
    ]
    
    # Process each branch separately
    for branch in Branch.query.all():
        branch_id = branch.id
        
        for days_before, sent_flag, template_type in reminders:
            target_date = today + timedelta(days=days_before)
            
            # Find events needing this reminder
            events = Event.query.filter(
                Event.branch_id == branch_id,
                Event.event_date == target_date,
                Event.sms_reminder_enabled == True,
                getattr(Event, f'sms_reminder_{days_before}') == True,
                getattr(Event, sent_flag) == False
            ).all()
            
            for event in events:
                queued = process_event_reminder(event, branch_id, days_before, template_type)
                total_queued += queued
                
                # Mark reminder as sent
                setattr(event, sent_flag, True)
                db.session.commit()
    
    if total_queued > 0:
        logger.info(f"Event reminder job queued {total_queued} SMS total")
    else:
        logger.info("No event reminders due today")

def process_event_reminder(event, branch_id, days_until, template_type):
    """Send reminder SMS to all members and visitors in the branch"""
    
    template = get_rotated_template(None, template_type)
    if not template:
        logger.warning(f"No template found for {template_type}")
        return 0
    
    queued = 0
    
    # Get all members with phones in this branch
    members = Member.query.filter(
        Member.branch_id == branch_id,
        Member.phone.isnot(None)
    ).all()
    
    for member in members:
        if send_event_sms(member, event, days_until, template, branch_id):
            queued += 1
    
    # Get all visitors with phones in this branch
    visitors = Visitor.query.filter(
        Visitor.branch_id == branch_id,
        Visitor.phone.isnot(None)
    ).all()
    
    for visitor in visitors:
        if send_event_sms(visitor, event, days_until, template, branch_id):
            queued += 1
    
    logger.info(f"Queued {queued} reminders for '{event.title}' ({days_until} days)")
    return queued

def send_event_sms(person, event, days_until, template, branch_id):
    """Create SMS log for event reminder"""
    
    # Check if already sent to this person for this event
    existing = SMSLog.query.filter(
        SMSLog.branch_id == branch_id,
        SMSLog.phone == person.phone,
        SMSLog.message_type == template.message_type,
        SMSLog.related_table == 'event',
        SMSLog.related_id == event.id
    ).first()
    
    if existing:
        return False
    
    # Build message with variables
    message = template.message
    message = message.replace("{name}", person.first_name)
    message = message.replace("{event_title}", event.title)
    message = message.replace("{event_date}", event.event_date.strftime("%d %B %Y"))
    message = message.replace("{days_until}", str(days_until))
    
    sms = SMSLog(
        phone=person.phone,
        message=message,
        message_type=template.message_type,
        related_table='event',
        related_id=event.id,
        status='pending',
        branch_id=branch_id,
        template_id=template.id
    )
    
    db.session.add(sms)
    return True