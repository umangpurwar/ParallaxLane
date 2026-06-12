from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction, IntegrityError
from django.db.models import Prefetch
from .models import Question, Answer, ExamAttempt, Exam, QuestionOption
from django.utils.timezone import now
from core.permissions import IsOrgMember, IsOrgAdmin
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .serializers import ExamListSerializer
from .serializers import ExamSerializer, ExamDetailSerializer
from monitoring.models import Violation


class ExamListView(generics.ListAPIView):
    serializer_class = ExamListSerializer
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True)


class ExamDetailView(generics.RetrieveAPIView):
    serializer_class = ExamDetailSerializer
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True).prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("order").prefetch_related("options"),
            )
        )


class StartExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, pk):
        org = request.user.current_organisation

        with transaction.atomic():
            try:
                exam = Exam.objects.select_for_update().get(pk=pk, organisation=org)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=404)

            if not exam.is_active:
                return Response({"error": "Exam is disabled"}, status=403)

            if now() > exam.end_time:
                return Response({"error": "Exam period has ended"}, status=403)

            existing = ExamAttempt.objects.filter(
                user=request.user, exam=exam, status="active"
            ).first()

            if existing:
                return Response({
                    "attempt_id": existing.id,
                    "exam_id": exam.id,
                    "resumed": True,
                })

            already_done = ExamAttempt.objects.filter(
                user=request.user, exam=exam, status__in=["completed", "terminated"]
            ).exists()

            if already_done:
                return Response({"error": "You have already attempted this exam"}, status=400)

            try:
                attempt = ExamAttempt.objects.create(user=request.user, exam=exam)
            except IntegrityError:
                existing = ExamAttempt.objects.filter(
                    user=request.user, exam=exam, status="active"
                ).first()
                if existing:
                    return Response({
                        "attempt_id": existing.id,
                        "exam_id": exam.id,
                        "resumed": True,
                    })
                raise

        return Response({
            "attempt_id": attempt.id,
            "exam_id": exam.id,
            "resumed": False,
        })


class SubmitExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='3/m', method='POST', block=True))
    def post(self, request, pk):
        user = request.user
        org = user.current_organisation

        with transaction.atomic():
            try:
                exam = Exam.objects.select_for_update().get(pk=pk, organisation=org)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=404)

            attempt = ExamAttempt.objects.select_for_update().filter(
                user=user, exam=exam, status="active"
            ).first()

            if not attempt:
                return Response({"error": "No active exam attempt found"}, status=400)

            if attempt.status == "terminated":
                return Response({"error": "Exam has been terminated"}, status=403)

            if attempt.status == "completed":
                return Response({"error": "Exam already submitted"}, status=400)

            answers = request.data.get("answers", {})
            if not isinstance(answers, dict):
                return Response({"error": "answers must be an object"}, status=400)

            questions = list(
                exam.questions.prefetch_related("options").all()
            )
            question_count = len(questions)
            if len(answers) > question_count:
                return Response(
                    {"error": f"Too many answers submitted (max {question_count})"},
                    status=400,
                )

            questions_by_id = {q.id: q for q in questions}
            options_by_question = {
                q.id: {o.id: o for o in q.options.all()} for q in questions
            }
            existing_answer_qids = set(
                Answer.objects.filter(attempt=attempt).values_list("question_id", flat=True)
            )

            score = 0
            total_points = sum(q.points for q in questions)
            answers_to_create = []

            for question_id_raw, submitted_answer in answers.items():
                try:
                    question_id = int(question_id_raw)
                except (TypeError, ValueError):
                    continue

                question = questions_by_id.get(question_id)
                if not question:
                    continue

                if question_id in existing_answer_qids:
                    continue

                is_correct = False
                option_map = options_by_question.get(question_id, {})

                if question.question_type in ["mcq", "true_false"]:
                    try:
                        option_id = int(submitted_answer)
                    except (TypeError, ValueError):
                        continue
                    option = option_map.get(option_id)
                    if not option:
                        continue

                    answer = Answer(
                        attempt=attempt,
                        question=question,
                        selected_option=option,
                    )
                    if option.is_correct:
                        score += question.points
                        is_correct = True
                    else:
                        score -= question.negative_points
                    answer.is_correct = is_correct
                    answers_to_create.append(answer)

                elif question.question_type == "short_answer":
                    answer = Answer(
                        attempt=attempt,
                        question=question,
                        text_answer=submitted_answer,
                    )
                    correct = (question.correct_text_answer or "").strip().lower()
                    user_ans = str(submitted_answer).strip().lower()
                    if correct and user_ans == correct:
                        score += question.points
                        is_correct = True
                    else:
                        score -= question.negative_points
                    answer.is_correct = is_correct
                    answers_to_create.append(answer)

                elif question.question_type in ["file_upload", "image_based"]:
                    answers_to_create.append(
                        Answer(attempt=attempt, question=question, is_correct=None)
                    )

            if answers_to_create:
                Answer.objects.bulk_create(answers_to_create)
            attempt.points_scored = score
            attempt.total_points = total_points
            attempt.status = "completed"
            attempt.end_time = now()
            attempt.save()

        return Response({
            "message": "Exam submitted successfully",
            "points_scored": score,
            "total_points": total_points,
            "total_questions": question_count,
        })


@api_view(['GET'])
@permission_classes([IsOrgMember])
def my_results(request):
    org = request.user.current_organisation
    attempts = ExamAttempt.objects.filter(
        user=request.user,
        exam__organisation=org,
        status__in=['completed', 'terminated']
    ).select_related('exam').prefetch_related('exam__questions')

    data = []
    for attempt in attempts:
        data.append({
            "attempt_id": attempt.id,
            "exam_title": attempt.exam.title,
            "points_scored": attempt.points_scored or 0,
            "total_points": attempt.total_points or 0,
            "total_questions": attempt.exam.questions.count(),
            "violations": attempt.total_violations,
            "status": attempt.status.capitalize(),
            "date": attempt.start_time
        })

    return Response(data)


class CreateExamView(generics.CreateAPIView):
    serializer_class = ExamSerializer
    permission_classes = [IsOrgAdmin]

    @method_decorator(ratelimit(key='user', rate='2/m', method='POST', block=True))
    def perform_create(self, serializer):
        org = self.request.user.current_organisation
        serializer.save(
            created_by=self.request.user,
            organisation=org
        )
