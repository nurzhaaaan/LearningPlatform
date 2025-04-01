from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import Assignment, Course, Enrollment, AssignmentSubmission, User
from forms import AssignmentForm, AssignmentSubmissionForm, GradeAssignmentForm
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

assignments = Blueprint('assignments', __name__)

@assignments.route('/courses/<int:course_id>/assignments/create', methods=['GET', 'POST'])
@login_required
def create(course_id):
    """Create a new assignment (teacher or admin only)"""
    course = Course.query.get_or_404(course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = AssignmentForm()
    
    if form.validate_on_submit():
        try:
            assignment = Assignment(
                title=form.title.data,
                description=form.description.data,
                due_date=form.due_date.data,
                points=form.points.data,
                course_id=course.id
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            flash(f'Assignment "{assignment.title}" has been created.', 'success')
            return redirect(url_for('courses.view', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating assignment: {str(e)}")
            flash('Error creating assignment. Please try again.', 'danger')
    
    return render_template('assignments/create.html', form=form, course=course)

@assignments.route('/assignments/<int:assignment_id>')
@login_required
def view(assignment_id):
    """View an assignment and its submissions"""
    assignment = Assignment.query.get_or_404(assignment_id)
    course = Course.query.get_or_404(assignment.course_id)
    
    # Check permission: teacher of the course, admin, or enrolled student
    if current_user.id == course.teacher_id or current_user.is_admin():
        # Teachers and admins can see all submissions
        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()
        
        # Prepare submission data
        submission_data = []
        for sub in submissions:
            student = User.query.get(sub.student_id)
            submission_data.append({
                'id': sub.id,
                'student_name': f"{student.first_name} {student.last_name}",
                'student_id': student.id,
                'submitted_at': sub.submitted_at,
                'grade': sub.grade,
                'feedback': sub.feedback,
                'is_graded': sub.grade is not None
            })
        
        return render_template(
            'assignments/view.html',
            assignment=assignment,
            course=course,
            submissions=submission_data,
            is_teacher=True
        )
    
    elif current_user.is_student():
        # Students need to be enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id,
            is_active=True
        ).first()
        
        if not enrollment:
            flash('You must be enrolled in this course to view its assignments.', 'warning')
            return redirect(url_for('courses.view', course_id=course.id))
        
        # Check if student has already submitted
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id
        ).first()
        
        return render_template(
            'assignments/view.html',
            assignment=assignment,
            course=course,
            submission=submission,
            is_teacher=False,
            is_past_due=datetime.utcnow() > assignment.due_date
        )
    
    else:
        abort(403)  # Forbidden

@assignments.route('/assignments/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(assignment_id):
    """Edit an assignment (teacher or admin only)"""
    assignment = Assignment.query.get_or_404(assignment_id)
    course = Course.query.get_or_404(assignment.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = AssignmentForm(obj=assignment)
    
    if form.validate_on_submit():
        try:
            assignment.title = form.title.data
            assignment.description = form.description.data
            assignment.due_date = form.due_date.data
            assignment.points = form.points.data
            
            db.session.commit()
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('assignments.view', assignment_id=assignment.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating assignment: {str(e)}")
            flash('Error updating assignment. Please try again.', 'danger')
    
    return render_template('assignments/create.html', form=form, course=course, assignment=assignment, edit_mode=True)

@assignments.route('/assignments/<int:assignment_id>/delete', methods=['POST'])
@login_required
def delete(assignment_id):
    """Delete an assignment (teacher or admin only)"""
    assignment = Assignment.query.get_or_404(assignment_id)
    course = Course.query.get_or_404(assignment.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    try:
        db.session.delete(assignment)
        db.session.commit()
        flash(f'Assignment "{assignment.title}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting assignment: {str(e)}")
        flash('Error deleting assignment. Please try again.', 'danger')
    
    return redirect(url_for('courses.view', course_id=course.id))

@assignments.route('/assignments/<int:assignment_id>/submit', methods=['GET', 'POST'])
@login_required
def submit(assignment_id):
    """Submit an assignment (students only)"""
    if not current_user.is_student():
        abort(403)  # Forbidden
    
    assignment = Assignment.query.get_or_404(assignment_id)
    course = Course.query.get_or_404(assignment.course_id)
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id,
        is_active=True
    ).first_or_404()
    
    # Check if past due date
    is_past_due = datetime.utcnow() > assignment.due_date
    if is_past_due:
        flash('This assignment is past its due date. Contact your instructor if you need an extension.', 'warning')
        return redirect(url_for('assignments.view', assignment_id=assignment.id))
    
    # Check if already submitted
    existing_submission = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()
    
    if existing_submission:
        flash('You have already submitted this assignment.', 'info')
        return redirect(url_for('assignments.view', assignment_id=assignment.id))
    
    form = AssignmentSubmissionForm()
    
    if form.validate_on_submit():
        try:
            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                content=form.content.data,
                file_url=form.file_url.data,
                submitted_at=datetime.utcnow()
            )
            
            db.session.add(submission)
            db.session.commit()
            
            flash('Your assignment has been submitted successfully!', 'success')
            return redirect(url_for('assignments.view', assignment_id=assignment.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting assignment: {str(e)}")
            flash('Error submitting assignment. Please try again.', 'danger')
    
    return render_template('assignments/submit.html', form=form, assignment=assignment, course=course)

@assignments.route('/submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
def grade_submission(submission_id):
    """Grade a submission (teacher or admin only)"""
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    assignment = Assignment.query.get_or_404(submission.assignment_id)
    course = Course.query.get_or_404(assignment.course_id)
    student = User.query.get_or_404(submission.student_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = GradeAssignmentForm(obj=submission)
    
    if form.validate_on_submit():
        try:
            submission.grade = form.grade.data
            submission.feedback = form.feedback.data
            
            db.session.commit()
            flash(f'Grade submitted for {student.first_name} {student.last_name}.', 'success')
            return redirect(url_for('assignments.view', assignment_id=assignment.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error grading submission: {str(e)}")
            flash('Error saving grade. Please try again.', 'danger')
    
    return render_template(
        'assignments/grade.html',
        form=form,
        submission=submission,
        assignment=assignment,
        course=course,
        student=student
    )
