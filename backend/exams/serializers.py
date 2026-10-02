from rest_framework import serializers
from django.db import transaction
from .models import Exam, Question, QuestionOption, ExamAttempt, Answer
from organisations.plan_features import get_plan_features


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "text", "is_correct"]


class CandidateQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "text"]


class CandidateQuestionSerializer(serializers.ModelSerializer):
    options = CandidateQuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "question_type", "points", "order", "image", "options"]


VALID_QUESTION_TYPES = {c[0] for c in Question.QUESTION_TYPE_CHOICES}


MAX_POINTS = 1000
MAX_DURATION_MINUTES = 24 * 60


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "id", "text", "question_type", "points", "negative_points",
            "order", "image", "options", "correct_text_answer", "explanation",
        ]

    def validate_question_type(self, value):
        if value not in VALID_QUESTION_TYPES:
            raise serializers.ValidationError(f"Invalid question type: {value}")
        return value

    def validate_points(self, value):
        if value < 0:
            raise serializers.ValidationError("points must be >= 0")
        if value > MAX_POINTS:
            raise serializers.ValidationError(f"points must be <= {MAX_POINTS}")
        return value

    def validate_negative_points(self, value):
        if value < 0:
            raise serializers.ValidationError("negative_points must be >= 0")
        if value > MAX_POINTS:
            raise serializers.ValidationError(f"negative_points must be <= {MAX_POINTS}")
        return value

    def validate(self, attrs):
        if self.partial and "options" not in attrs and "question_type" not in attrs:
            return attrs
        q_type = attrs.get("question_type", getattr(self.instance, "question_type", "mcq"))
        options = attrs.get("options") or []
        correct = sum(1 for option in options if option.get("is_correct"))
        if q_type == "mcq" and (len(options) < 2 or correct != 1):
            raise serializers.ValidationError(
                "MCQ questions need at least 2 options and exactly one correct option"
            )
        if q_type == "true_false" and (len(options) != 2 or correct != 1):
            raise serializers.ValidationError(
                "True/false questions need exactly 2 options and one correct option"
            )
        if q_type == "short_answer" and not (
            attrs.get("correct_text_answer")
            or getattr(self.instance, "correct_text_answer", None)
        ):
            raise serializers.ValidationError("Short answer questions need correct_text_answer")
        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop("options", [])
        question = Question.objects.create(**validated_data)
        for option_data in options_data:
            QuestionOption.objects.create(question=question, **option_data)
        return question

    def update(self, instance, validated_data):
        options_data = validated_data.pop("options", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if options_data is not None:
            instance.options.all().delete()
            for option_data in options_data:
                QuestionOption.objects.create(question=instance, **option_data)
        return instance


class ExamSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Exam
        fields = [
            "id", "title", "description", "start_time", "end_time", "duration",
            "created_by", "organisation", "is_published", "is_active",
            "violation_limit", "auto_submit_on_violation", "created_at", "questions",
        ]
        # FIX: these are set by the view via save(), not by client
        read_only_fields = ["created_by", "organisation", "created_at", "id"]

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("duration must be greater than 0")
        if value > MAX_DURATION_MINUTES:
            raise serializers.ValidationError(f"duration must be <= {MAX_DURATION_MINUTES} minutes")
        return value

    def validate_violation_limit(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("violation_limit must be between 1 and 100")
        return value

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "end_time must be after start_time"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from organisations.models import Organisation
        request = self.context.get("request")
        org = Organisation.objects.select_for_update().get(id=request.user.current_organisation_id)

        if org.exams.count() >= org.max_exams:
            raise serializers.ValidationError({"error": f"Exam limit reached (max {org.max_exams})"})

        features = get_plan_features(org)
        allowed_types = features.get("allowed_question_types", [])
        questions_data = validated_data.pop("questions")

        if len(questions_data) > features["max_questions"]:
            raise serializers.ValidationError({"error": "Question limit exceeded for your plan"})

        for question_data in questions_data:
            q_type = question_data.get("question_type", "mcq")
            if q_type not in allowed_types:
                raise serializers.ValidationError({"error": f"Question type '{q_type}' not allowed in your plan"})
            if question_data.get("image") and not features["image_questions"]:
                raise serializers.ValidationError({"error": "Image-based questions not allowed in your plan"})
            if q_type == "file_upload" and not features["file_upload"]:
                raise serializers.ValidationError({"error": "File upload questions not allowed in your plan"})

        exam = Exam.objects.create(**validated_data)

        for question_data in questions_data:
            options_data = question_data.pop("options", [])
            question = Question.objects.create(exam=exam, **question_data)
            for option_data in options_data:
                QuestionOption.objects.create(question=question, **option_data)

        return exam

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        org = request.user.current_organisation
        features = get_plan_features(org)
        allowed_types = features.get("allowed_question_types", [])
        questions_data = validated_data.pop("questions", None)

        # Replacing questions would orphan graded answers: lock them once
        # anyone has started. Duplicate the exam to change questions.
        if questions_data is not None and ExamAttempt.objects.filter(exam=instance).exists():
            raise serializers.ValidationError({
                "error": "Questions are locked once any attempt exists. Duplicate the exam to change them."
            })

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if questions_data is not None:
            if len(questions_data) > features["max_questions"]:
                raise serializers.ValidationError({"error": "Question limit exceeded for your plan"})
            for question_data in questions_data:
                q_type = question_data.get("question_type", "mcq")
                if q_type not in allowed_types:
                    raise serializers.ValidationError({"error": f"Question type '{q_type}' not allowed in your plan"})
                if question_data.get("image") and not features["image_questions"]:
                    raise serializers.ValidationError({"error": "Image-based questions not allowed in your plan"})
                if q_type == "file_upload" and not features["file_upload"]:
                    raise serializers.ValidationError({"error": "File upload questions not allowed in your plan"})

            instance.questions.all().delete()
            for question_data in questions_data:
                options_data = question_data.pop("options", [])
                question = Question.objects.create(exam=instance, **question_data)
                for option_data in options_data:
                    QuestionOption.objects.create(question=question, **option_data)

        return instance


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "attempt", "question", "selected_option", "text_answer", "file_upload", "is_correct"]


class ExamAttemptSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = ExamAttempt
        fields = [
            "id", "user", "exam", "start_time", "deadline", "end_time",
            "points_scored", "total_points", "risk_score",
            "total_violations", "status", "last_active", "answers",
        ]


class ExamDetailSerializer(serializers.ModelSerializer):
    questions = CandidateQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "description", "duration", "start_time", "end_time", "is_active", "is_published", "questions"]


class ExamListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ["id", "title", "description", "duration", "start_time", "end_time", "is_active"]
