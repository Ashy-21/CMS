# student_management_app/context_processors.py
from .models import College

def college_profile(request):
    """
    Provide 'college_profile' (selected college) and 'colleges' (all colleges).
    The selected college is stored in session as 'selected_college_id'.
    """
    colleges = College.objects.all()
    selected_college = None
    college_id = request.session.get('selected_college_id')
    if college_id:
        selected_college = College.objects.filter(id=college_id).first()
    return {
        'college_profile': selected_college,
        'colleges': colleges,
    }
