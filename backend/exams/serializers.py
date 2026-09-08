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
        return value

    def validate_negative_points(self, value):
        if value < 0:
            raise serializers.ValidationError("negative_points must be >= 0")
        return value

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
        return value

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

        if questions_data is not None and ExamAttempt.objects.filter(
            exam=instance,
            status="active",
            answers__isnull=False,
        ).exists():
            raise serializers.ValidationError({
                "error": "Cannot replace questions while an active attempt has saved answers."
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
