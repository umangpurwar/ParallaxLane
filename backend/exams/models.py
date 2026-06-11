from django.db import models
from django.conf import settings
from django.utils.timezone import now

User = settings.AUTH_USER_MODEL


# =========================
# EXAM
# =========================
class Exam(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes")

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='exams'
    )

    is_published = models.BooleanField(default=True)
    is_active = models.BooleanField(default=False)

    violation_limit = models.IntegerField(default=5)
    auto_submit_on_violation = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# =========================
# QUESTION
# =========================
class Question(models.Model):

    QUESTION_TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("true_false", "True/False"),
        ("short_answer", "Short Answer"),
        ("image_based", "Image Based"),
        ("file_upload", "File Upload"),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    text = models.TextField()

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default="mcq"
    )

    # scoring
    points = models.IntegerField(default=1)
    negative_points = models.FloatField(default=0)

    order = models.IntegerField(default=0)

    # media (for puzzles etc.)
    image = models.URLField(blank=True, null=True)

    # short answer correct text
    correct_text_answer = models.TextField(blank=True, null=True)

    # explanation (premium feature)
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.text[:50]}..."


# =========================
# OPTIONS (MCQ / TRUE-FALSE)
# =========================
class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )

    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


# =========================
# EXAM ATTEMPT
# =========================
class ExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, db_index=True)

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    # scoring
    points_scored = models.FloatField(default=0)
    total_points = models.FloatField(default=0)

    risk_score = models.IntegerField(default=0)
    total_violations = models.IntegerField(default=0)

    status = models.CharField(max_length=20, default="active", db_index=True)
    last_active = models.DateTimeField(default=now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exam"],
                condition=models.Q(status="active"),
                name="unique_active_attempt_per_user_exam",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.exam}"


# =========================
# ANSWERS
# =========================
class Answer(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    # MCQ / TRUE-FALSE
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # SHORT ANSWER
    text_answer = models.TextField(blank=True, null=True)

    # FILE UPLOAD / PUZZLE
    file_upload = models.FileField(
        upload_to="answers/",
        null=True,
        blank=True
    )

    is_correct = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.attempt} - {self.question}"