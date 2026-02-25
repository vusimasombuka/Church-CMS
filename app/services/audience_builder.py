from app.models.member import Member
from app.models.lookup import Lookup
from app.utils import normalize_sa_phone
from datetime import datetime, date
from sqlalchemy import func, and_, or_
from app.extensions import db

class AudienceBuilder:
    """Builds dynamic audience queries based on filters"""
    
    @staticmethod
    def get_available_filters():
        """Returns filter configuration for UI"""
        # Get dynamic options from database
        departments = Lookup.query.filter_by(category="department").all()
        marital_statuses = Lookup.query.filter_by(category="marital_status").all()
        
        return {
            'gender': {
                'type': 'multi_select',
                'label': 'Gender',
                'options': [
                    {'value': 'male', 'label': 'Male'},
                    {'value': 'female', 'label': 'Female'}
                ]
            },
            'marital_status': {
                'type': 'multi_select',
                'label': 'Marital Status',
                'options': [{'value': s.value, 'label': s.value} for s in marital_statuses]
            },
            'department': {
                'type': 'multi_select',
                'label': 'Department',
                'options': [{'value': d.value, 'label': d.value} for d in departments]
            },
            'baptized': {
                'type': 'boolean',
                'label': 'Baptized'
            },
            'membership_course': {
                'type': 'boolean',
                'label': 'Completed Membership Course'
            },
            'member_status': {
            'type': 'multi_select',
            'label': 'Member Status',
            'options': [{'value': s.value, 'label': s.value} for s in Lookup.query.filter_by(category="member_status", is_active=True).all()]
            },
            'age_range': {
                'type': 'range',
                'label': 'Age Range',
                'min': 0,
                'max': 100
            }
        }
    
    @staticmethod
    def build_query(filters, branch_id=None, require_phone=True):
        """
        Builds query based on filter criteria
        
        filters format:
        {
            "gender": ["male"],
            "baptized": true,
            "department": ["Ushering"]
        }
        """
        query = Member.query
        
        # Branch isolation
        if branch_id:
            query = query.filter(Member.branch_id == branch_id)
        
        # Must have phone number for SMS
        if require_phone:
            query = query.filter(
                Member.phone != None,
                Member.phone != ''
            )
        
        if not filters:
            return query
        
        # Gender filter
        if filters.get('gender'):
            query = query.filter(Member.gender.in_(filters['gender']))
        
        # Marital status
        if filters.get('marital_status'):
            query = query.filter(Member.marital_status.in_(filters['marital_status']))
        
        # Department
        if filters.get('department'):
            query = query.filter(Member.department.in_(filters['department']))
        
        # Baptized
        if filters.get('baptized') is not None:
            query = query.filter(Member.baptized == filters['baptized'])
        
        # Membership course
        if filters.get('membership_course') is not None:
            query = query.filter(Member.membership_course == filters['membership_course'])
        
        # Member status
        if filters.get('member_status'):
            query = query.filter(Member.member_status.in_(filters['member_status']))
        
        # Age range
        if filters.get('age_range'):
            min_age = filters['age_range'].get('min', 0)
            max_age = filters['age_range'].get('max', 100)
            
            today = date.today()
            min_date = today.replace(year=today.year - max_age - 1)
            max_date = today.replace(year=today.year - min_age)
            
            query = query.filter(
                Member.date_of_birth.between(min_date, max_date)
            )
        
        return query
    
    @staticmethod
    def get_count(filters, branch_id=None):
        """Get count of matching members"""
        query = AudienceBuilder.build_query(filters, branch_id)
        return query.count()
    
    @staticmethod
    def get_recipients_paginated(filters, page=1, per_page=50, branch_id=None):
        """Get paginated list of recipients"""
        query = AudienceBuilder.build_query(filters, branch_id)
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def personalize_message(content, member):
        """Replace placeholders with member data"""
        replacements = {
            '{{first_name}}': member.first_name or '',
            '{{last_name}}': member.last_name or '',
            '{{full_name}}': f"{member.first_name or ''} {member.last_name or ''}".strip(),
            '{{department}}': member.department or '',
            '{{phone}}': member.phone or ''
        }
        
        result = content
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result