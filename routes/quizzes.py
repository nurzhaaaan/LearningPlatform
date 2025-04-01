from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import Quiz, Course, Enrollment, Question, QuestionOption, QuizAttempt, QuizAnswer, User
from forms import QuizForm, QuestionForm, OptionForm
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

quizzes = Blueprint('quizzes', __name__)

@quizzes.route('/courses/<int:course_id>/quizzes/create', methods=['GET', 'POST'])
@login_required
def create(course_id):
    """Create a new quiz (teacher or admin only)"""
    course = Course.query.get_or_404(course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = QuizForm()
    
    if form.validate_on_submit():
        try:
            quiz = Quiz(
                title=form.title.data,
                description=form.description.data,
                time_limit=form.time_limit.data,
                course_id=course.id,
                is_active=form.is_active.data
            )
            
            db.session.add(quiz)
            db.session.commit()
            
            flash(f'Quiz "{quiz.title}" has been created. Now add questions to it.', 'success')
            return redirect(url_for('quizzes.add_question', quiz_id=quiz.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating quiz: {str(e)}")
            flash('Error creating quiz. Please try again.', 'danger')
    
    return render_template('quizzes/create.html', form=form, course=course)

@quizzes.route('/quizzes/<int:quiz_id>/add_question', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    """Add a question to a quiz (teacher or admin only)"""
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = QuestionForm()
    
    if form.validate_on_submit():
        try:
            question = Question(
                quiz_id=quiz.id,
                question_text=form.question_text.data,
                question_type=form.question_type.data,
                points=form.points.data
            )
            
            db.session.add(question)
            db.session.commit()
            
            # Handle options for multiple choice
            if form.question_type.data == 'multiple_choice':
                option_count = int(request.form.get('option_count', 0))
                correct_option = request.form.get('correct_option')
                
                for i in range(1, option_count + 1):
                    option_text = request.form.get(f'option_text_{i}')
                    is_correct = str(i) == correct_option
                    
                    if option_text:
                        option = QuestionOption(
                            question_id=question.id,
                            option_text=option_text,
                            is_correct=is_correct
                        )
                        db.session.add(option)
            
            # Handle true/false options
            elif form.question_type.data == 'true_false':
                # Create "True" option
                true_option = QuestionOption(
                    question_id=question.id,
                    option_text="True",
                    is_correct=request.form.get('true_false') == 'true'
                )
                db.session.add(true_option)
                
                # Create "False" option
                false_option = QuestionOption(
                    question_id=question.id,
                    option_text="False",
                    is_correct=request.form.get('true_false') == 'false'
                )
                db.session.add(false_option)
            
            db.session.commit()
            
            if 'add_another' in request.form:
                flash('Question added successfully. Add another question.', 'success')
                return redirect(url_for('quizzes.add_question', quiz_id=quiz.id))
            else:
                flash('Question added successfully.', 'success')
                return redirect(url_for('quizzes.view', quiz_id=quiz.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding question: {str(e)}")
            flash('Error adding question. Please try again.', 'danger')
    
    # Get existing questions
    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    
    return render_template('quizzes/add_question.html', form=form, quiz=quiz, course=course, questions=questions)

@quizzes.route('/quizzes/<int:quiz_id>')
@login_required
def view(quiz_id):
    """View a quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check permission: teacher of the course, admin, or enrolled student
    if current_user.id == course.teacher_id or current_user.is_admin():
        # Teachers and admins see quiz details and all attempts
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        
        # Get all attempts for this quiz
        attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).all()
        
        # Prepare attempt data
        attempt_data = []
        for attempt in attempts:
            student = User.query.get(attempt.student_id)
            attempt_data.append({
                'id': attempt.id,
                'student_name': f"{student.first_name} {student.last_name}",
                'student_id': student.id,
                'started_at': attempt.started_at,
                'completed_at': attempt.completed_at,
                'score': attempt.score,
                'is_completed': attempt.completed_at is not None
            })
        
        return render_template(
            'quizzes/view.html',
            quiz=quiz,
            course=course,
            questions=questions,
            attempts=attempt_data,
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
            flash('You must be enrolled in this course to view its quizzes.', 'warning')
            return redirect(url_for('courses.view', course_id=course.id))
        
        # Check if student has already attempted this quiz
        attempts = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            student_id=current_user.id
        ).all()
        
        # Sort attempts by most recent first
        attempts.sort(key=lambda x: x.started_at, reverse=True)
        
        return render_template(
            'quizzes/view.html',
            quiz=quiz,
            course=course,
            attempts=attempts,
            is_teacher=False
        )
    
    else:
        abort(403)  # Forbidden

@quizzes.route('/quizzes/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
def take(quiz_id):
    """Take a quiz (students only)"""
    if not current_user.is_student():
        abort(403)  # Forbidden
    
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id,
        is_active=True
    ).first_or_404()
    
    # Check if quiz is active
    if not quiz.is_active:
        flash('This quiz is not currently active.', 'warning')
        return redirect(url_for('quizzes.view', quiz_id=quiz.id))
    
    # Create a new attempt if it's a GET request
    if request.method == 'GET':
        # Check for incomplete attempts
        incomplete_attempt = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            student_id=current_user.id,
            completed_at=None
        ).first()
        
        if incomplete_attempt:
            # Resume incomplete attempt
            attempt = incomplete_attempt
        else:
            # Create a new attempt
            attempt = QuizAttempt(
                quiz_id=quiz.id,
                student_id=current_user.id,
                started_at=datetime.utcnow()
            )
            db.session.add(attempt)
            db.session.commit()
        
        # Get questions
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        
        # For each question, get its options
        for question in questions:
            question.options = QuestionOption.query.filter_by(question_id=question.id).all()
        
        return render_template(
            'quizzes/take.html',
            quiz=quiz,
            course=course,
            questions=questions,
            attempt=attempt
        )
    
    # Process quiz submission
    elif request.method == 'POST':
        attempt_id = request.form.get('attempt_id')
        attempt = QuizAttempt.query.get_or_404(attempt_id)
        
        # Check if this attempt belongs to the current user
        if attempt.student_id != current_user.id:
            abort(403)  # Forbidden
        
        # Check if the attempt is already completed
        if attempt.completed_at:
            flash('This quiz attempt has already been submitted.', 'warning')
            return redirect(url_for('quizzes.results', attempt_id=attempt.id))
        
        try:
            # Get all questions
            questions = Question.query.filter_by(quiz_id=quiz.id).all()
            
            total_points = 0
            earned_points = 0
            
            # Process each question
            for question in questions:
                total_points += question.points
                
                # Get selected option(s)
                selected_option_id = request.form.get(f'question_{question.id}')
                
                # For multiple choice questions
                if selected_option_id:
                    selected_option = QuestionOption.query.get(selected_option_id)
                    
                    # Create answer record
                    answer = QuizAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        selected_option_id=selected_option.id,
                        is_correct=selected_option.is_correct
                    )
                    
                    if selected_option.is_correct:
                        earned_points += question.points
                
                # Handle no selection
                else:
                    answer = QuizAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        is_correct=False
                    )
                
                db.session.add(answer)
            
            # Calculate score as percentage
            score = round((earned_points / total_points) * 100) if total_points > 0 else 0
            
            # Update attempt
            attempt.completed_at = datetime.utcnow()
            attempt.score = score
            
            db.session.commit()
            
            flash(f'Quiz submitted successfully! Your score: {score}%', 'success')
            return redirect(url_for('quizzes.results', attempt_id=attempt.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting quiz: {str(e)}")
            flash('Error submitting quiz. Please try again.', 'danger')
            return redirect(url_for('quizzes.take', quiz_id=quiz.id))

@quizzes.route('/quiz_attempts/<int:attempt_id>/results')
@login_required
def results(attempt_id):
    """View quiz results"""
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    quiz = Quiz.query.get_or_404(attempt.quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check permissions
    if current_user.id != attempt.student_id and current_user.id != course.teacher_id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get all answers for this attempt
    answers = QuizAnswer.query.filter_by(attempt_id=attempt.id).all()
    
    # Organize answers by question
    result_data = []
    for answer in answers:
        question = Question.query.get(answer.question_id)
        selected_option = QuestionOption.query.get(answer.selected_option_id) if answer.selected_option_id else None
        correct_option = QuestionOption.query.filter_by(question_id=question.id, is_correct=True).first()
        
        result_data.append({
            'question_text': question.question_text,
            'points': question.points,
            'selected_text': selected_option.option_text if selected_option else "No answer",
            'correct_text': correct_option.option_text if correct_option else "N/A",
            'is_correct': answer.is_correct
        })
    
    # Get student info
    student = User.query.get(attempt.student_id)
    
    return render_template(
        'quizzes/results.html',
        attempt=attempt,
        quiz=quiz,
        course=course,
        results=result_data,
        student=student
    )

@quizzes.route('/quizzes/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(quiz_id):
    """Edit a quiz (teacher or admin only)"""
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = QuizForm(obj=quiz)
    
    if form.validate_on_submit():
        try:
            quiz.title = form.title.data
            quiz.description = form.description.data
            quiz.time_limit = form.time_limit.data
            quiz.is_active = form.is_active.data
            
            db.session.commit()
            flash('Quiz updated successfully!', 'success')
            return redirect(url_for('quizzes.view', quiz_id=quiz.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating quiz: {str(e)}")
            flash('Error updating quiz. Please try again.', 'danger')
    
    return render_template('quizzes/create.html', form=form, course=course, quiz=quiz, edit_mode=True)

@quizzes.route('/quizzes/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete(quiz_id):
    """Delete a quiz (teacher or admin only)"""
    quiz = Quiz.query.get_or_404(quiz_id)
    course = Course.query.get_or_404(quiz.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    try:
        db.session.delete(quiz)
        db.session.commit()
        flash(f'Quiz "{quiz.title}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting quiz: {str(e)}")
        flash('Error deleting quiz. Please try again.', 'danger')
    
    return redirect(url_for('courses.view', course_id=course.id))
