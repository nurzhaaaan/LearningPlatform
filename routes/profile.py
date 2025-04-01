from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Course, Enrollment, Assignment, AssignmentSubmission, QuizAttempt
from forms import ProfileForm
from werkzeug.security import check_password_hash
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

profile = Blueprint('profile', __name__)

@profile.route('/profile')
@login_required
def view_profile():
    """View user profile"""
    # Get enrolled courses for students
    enrolled_courses = []
    if current_user.is_student():
        for enrollment in current_user.enrollments:
            if enrollment.is_active:
                course = enrollment.course
                teacher = User.query.get(course.teacher_id)
                
                # Calculate completion percentage (mock data for now)
                completion = 45  # This would be calculated based on assignments, quizzes, etc.
                
                enrolled_courses.append({
                    'id': course.id,
                    'title': course.title,
                    'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                    'completion': completion
                })
    
    # Get courses taught by teachers
    courses_teaching = []
    if current_user.is_teacher():
        for course in current_user.courses_teaching:
            student_count = Enrollment.query.filter_by(course_id=course.id, is_active=True).count()
            courses_teaching.append({
                'id': course.id,
                'title': course.title,
                'code': course.code,
                'students': student_count
            })
    
    # Get recent assignment submissions for teacher
    submissions_to_grade = 0
    recent_submissions = []
    if current_user.is_teacher():
        # Get courses taught by this teacher
        course_ids = [course.id for course in current_user.courses_teaching]
        
        # Get assignments for these courses
        assignment_ids = db.session.query(Assignment.id).filter(Assignment.course_id.in_(course_ids)).all()
        assignment_ids = [a[0] for a in assignment_ids]
        
        # Get submissions that need grading
        ungraded_submissions = AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(assignment_ids),
            AssignmentSubmission.grade == None
        ).order_by(AssignmentSubmission.submitted_at.desc()).limit(10).all()
        
        submissions_to_grade = len(ungraded_submissions)
        
        for submission in ungraded_submissions:
            assignment = Assignment.query.get(submission.assignment_id)
            course = Course.query.get(assignment.course_id)
            student = User.query.get(submission.student_id)
            
            recent_submissions.append({
                'student_name': f"{student.first_name} {student.last_name}",
                'assignment_title': assignment.title,
                'course_title': course.title,
                'submitted_at': submission.submitted_at.strftime('%Y-%m-%d %H:%M'),
                'is_graded': False,
                'link': url_for('assignments.grade_submission', submission_id=submission.id)
            })
    
    # Get upcoming deadlines for student
    upcoming_deadlines = []
    if current_user.is_student():
        # Get courses student is enrolled in
        enrollment_course_ids = [e.course_id for e in current_user.enrollments if e.is_active]
        
        # Get assignments for these courses that are due in the future
        upcoming_assignments = Assignment.query.filter(
            Assignment.course_id.in_(enrollment_course_ids),
            Assignment.due_date > datetime.utcnow()
        ).order_by(Assignment.due_date).limit(10).all()
        
        for assignment in upcoming_assignments:
            course = Course.query.get(assignment.course_id)
            
            # Check if already submitted
            submission = AssignmentSubmission.query.filter_by(
                assignment_id=assignment.id,
                student_id=current_user.id
            ).first()
            
            status = 'submitted' if submission else 'pending'
            
            upcoming_deadlines.append({
                'title': assignment.title,
                'course': course.title,
                'due_date': assignment.due_date.strftime('%Y-%m-%d %H:%M'),
                'status': status,
                'link': url_for('assignments.view', assignment_id=assignment.id)
            })
    
    # Get activity data
    activities = [
        {
            'type': 'Login',
            'type_color': 'primary',
            'description': 'You logged in to the system',
            'time': '2 minutes ago'
        },
        {
            'type': 'Course',
            'type_color': 'success',
            'description': 'You viewed Python Programming course',
            'time': '1 hour ago'
        },
        {
            'type': 'Assignment',
            'type_color': 'info',
            'description': 'You submitted Project Milestone 1',
            'time': '2 days ago'
        }
    ]
    
    # Get announcement data
    announcements = [
        {
            'title': 'Platform Maintenance',
            'content': 'The LMS will be undergoing maintenance this weekend. Please complete any pending assignments before Saturday.',
            'date': '2 days ago',
            'source': 'System Administrator'
        }
    ]
    
    # Get stats based on user role
    if current_user.is_student():
        # Calculate student stats
        total_students = User.query.filter_by(role='student').count()
        completed_assignments = AssignmentSubmission.query.filter_by(student_id=current_user.id).count()
        
        # Calculate average grade
        submissions = AssignmentSubmission.query.filter_by(student_id=current_user.id).all()
        grades = [s.grade for s in submissions if s.grade is not None]
        avg_grade = sum(grades) / len(grades) if grades else 0
        
        # Count pending tasks
        pending_tasks = Assignment.query.join(Course).join(Enrollment).filter(
            Enrollment.student_id == current_user.id,
            Enrollment.is_active == True,
            Assignment.due_date > datetime.utcnow()
        ).count()
        
        stats = {
            'enrolled_courses': enrolled_courses,
            'completed_assignments': completed_assignments,
            'avg_grade': int(avg_grade),
            'pending_tasks': pending_tasks,
            'upcoming_deadlines': upcoming_deadlines,
        }
    
    elif current_user.is_teacher():
        # Calculate teacher stats
        total_students = Enrollment.query.join(Course).filter(
            Course.teacher_id == current_user.id,
            Enrollment.is_active == True
        ).count()
        
        active_assignments = Assignment.query.join(Course).filter(
            Course.teacher_id == current_user.id,
            Assignment.due_date > datetime.utcnow()
        ).count()
        
        stats = {
            'courses_teaching': courses_teaching,
            'total_students': total_students,
            'active_assignments': active_assignments,
            'submissions_to_grade': submissions_to_grade,
            'recent_submissions': recent_submissions,
        }
    
    return render_template(
        'dashboard.html',
        enrolled_courses=enrolled_courses,
        courses_teaching=courses_teaching,
        activities=activities,
        announcements=announcements,
        upcoming_deadlines=upcoming_deadlines,
        recent_submissions=recent_submissions,
        **stats
    )

@profile.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            if form.current_password.data:
                # Validate current password if trying to change password
                if not current_user.check_password(form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return render_template('profile.html', form=form, edit_mode=True)
                
                # Check if new password is provided and matches confirmation
                if form.new_password.data:
                    if form.new_password.data != form.confirm_password.data:
                        flash('New password and confirmation do not match.', 'danger')
                        return render_template('profile.html', form=form, edit_mode=True)
                    
                    # Update password
                    current_user.set_password(form.new_password.data)
            
            # Update other fields
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('profile.view_profile'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.', 'danger')
    
    return render_template('profile.html', form=form, edit_mode=True)
