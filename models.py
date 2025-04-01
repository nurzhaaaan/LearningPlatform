from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# User roles
class Role:
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.STUDENT)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_code = db.Column(db.String(6))
    reset_code_expires = db.Column(db.DateTime)
    
    # Relationships
    courses_teaching = db.relationship('Course', backref='teacher', lazy=True, 
                                       foreign_keys='Course.teacher_id')
    enrollments = db.relationship('Enrollment', backref='student', lazy=True,
                                  cascade="all, delete-orphan")
    submissions = db.relationship('AssignmentSubmission', backref='student', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == Role.ADMIN
    
    def is_teacher(self):
        return self.role == Role.TEACHER
    
    def is_student(self):
        return self.role == Role.STUDENT
    
    def __repr__(self):
        return f'<User {self.username}>'
        
    def generate_reset_code(self):
        """Generate a random 6-digit code for password reset and set expiration time to 30 minutes from now"""
        import random
        import string
        from datetime import datetime, timedelta
        
        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        self.reset_code = code
        self.reset_code_expires = datetime.utcnow() + timedelta(minutes=30)
        
        return code
        
    def verify_reset_code(self, code):
        """Verify if the provided code matches and hasn't expired"""
        if not self.reset_code or not self.reset_code_expires:
            return False
            
        if datetime.utcnow() > self.reset_code_expires:
            # Code has expired
            return False
            
        return self.reset_code == code
        
    def clear_reset_code(self):
        """Clear the reset code after it's been used"""
        self.reset_code = None
        self.reset_code_expires = None


class ExamType:
    IELTS = 'ielts'
    SAT = 'sat'
    NUET = 'nuet'
    UTO = 'uto'
    GENERAL = 'general'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    exam_type = db.Column(db.String(20), default=ExamType.GENERAL)
    difficulty_level = db.Column(db.String(20), default='intermediate')
    duration_weeks = db.Column(db.Integer, default=8)
    
    # Relationships
    materials = db.relationship('Material', backref='course', lazy=True, 
                                cascade="all, delete-orphan")
    assignments = db.relationship('Assignment', backref='course', lazy=True, 
                                  cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, 
                                  cascade="all, delete-orphan")
    quizzes = db.relationship('Quiz', backref='course', lazy=True,
                             cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.title}>'


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Ensure a student can only enroll once in a course
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id'),)
    
    def __repr__(self):
        return f'<Enrollment {self.student_id}-{self.course_id}>'


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(255))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Material {self.title}>'


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    points = db.Column(db.Integer, default=100)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True,
                                 cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Assignment {self.title}>'


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    
    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id'),)
    
    def __repr__(self):
        return f'<AssignmentSubmission {self.assignment_id}-{self.student_id}>'


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    time_limit = db.Column(db.Integer, nullable=False)  # in minutes
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True,
                               cascade="all, delete-orphan")
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)
    
    def __repr__(self):
        return f'<Quiz {self.title}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, etc.
    points = db.Column(db.Integer, default=1)
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy=True,
                             cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Question {self.id}>'


class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<QuestionOption {self.id}>'


class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    score = db.Column(db.Integer)
    
    # Relationships
    answers = db.relationship('QuizAnswer', backref='attempt', lazy=True,
                             cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<QuizAttempt {self.quiz_id}-{self.student_id}>'


class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_option.id'))
    text_answer = db.Column(db.Text)  # For free text answers
    is_correct = db.Column(db.Boolean, default=False)
    
    question = db.relationship('Question')
    selected_option = db.relationship('QuestionOption')
    
    def __repr__(self):
        return f'<QuizAnswer {self.attempt_id}-{self.question_id}>'
