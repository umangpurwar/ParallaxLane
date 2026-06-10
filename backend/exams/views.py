from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
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
        return Exam.objects.filter(
            organisation=org,
            is_published=True
        )

class ExamDetailView(generics.RetrieveAPIView):

    serializer_class = ExamDetailSerializer
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(
            organisation=org,
            is_published=True
        )

class StartExamView(generics.GenericAPIView):

    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, pk):

        org = request.user.current_organisation

        try:
            exam = Exam.objects.get(pk=pk, organisation=org)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found"}, status=404)

        if not exam.is_active:
            return Response({"error": "Exam is disabled"}, status=403)
        

        if now() > exam.end_time:
            return Response({"error": "Exam period has ended"}, status=403)

        attempt = ExamAttempt.objects.create(
            user=request.user,
            exam=exam
        )

        return Response({
            "attempt_id": attempt.id,
            "exam_id": exam.id
        })
    

class SubmitExamView(generics.GenericAPIView):

    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='3/m', method='POST', block=True))
    def post(self, request, pk):

        user = request.user
        org = user.current_organisation

        # Validate exam
        try:
            exam = Exam.objects.get(pk=pk, organisation=org)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found"}, status=404)

        if not exam.is_active:
            return Response({"error": "Exam is disabled"}, status=403)
        
        if now() > exam.end_time:
            return Response({"error": "Exam period has ended"}, status=403)

        # Get latest attempt
        attempt = ExamAttempt.objects.filter(
            user=user,
            exam=exam
        ).last()

        if not attempt:
            return Response({"error": "No active exam attempt found"}, status=400)

        if attempt.status == "terminated":
            return Response({"error": "Exam has been terminated"}, status=403)

        if attempt.status == "completed":
            return Response({"error": "Exam already submitted"}, status=400)

        answers = request.data.get("answers", {})

        score = 0
        total_points = 0

        # Process answers
        for question_id, submitted_answer in answers.items():
            try:
                question = Question.objects.get(id=question_id, exam=exam)

                # Prevent duplicate answers
                if Answer.objects.filter(
                    attempt=attempt,
                    question=question
                ).exists():
                    continue

                is_correct = False
                total_points += question.points

                # =========================
                # MCQ / TRUE-FALSE
                # =========================
                if question.question_type in ["mcq", "true_false"]:

                    try:
                        option = QuestionOption.objects.get(
                            id=submitted_answer,
                            question=question
                        )
                    except QuestionOption.DoesNotExist:
                        continue

                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=option
                    )

                    if option.is_correct:
                        score += question.points
                        is_correct = True
                    else:
                        score -= question.negative_points

                # =========================
                # SHORT ANSWER
                # =========================
                elif question.question_type == "short_answer":

                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        text_answer=submitted_answer
                    )

                    correct = (question.correct_text_answer or "").strip().lower()
                    user_ans = str(submitted_answer).strip().lower()

                    if correct and user_ans == correct:
                        score += question.points
                        is_correct = True
                    else:
                        score -= question.negative_points

                # =========================
                # FILE / IMAGE BASED (future-safe)
                # =========================
                elif question.question_type in ["file_upload", "image_based"]:

                    Answer.objects.create(
                        attempt=attempt,
                        question=question
                        # file handling can be added later
                    )

                    # no auto scoring
                    is_correct = None

                # Save correctness flag
                Answer.objects.filter(
                    attempt=attempt,
                    question=question
                ).update(is_correct=is_correct)

            except Question.DoesNotExist:
                continue

        # Save attempt
        attempt.points_scored = score
        attempt.total_points = total_points

        attempt.status = "completed"
        attempt.end_time = now()
        attempt.save()

        return Response({
    "message": "Exam submitted successfully",
    "points_scored": score,
    "total_points": total_points,
    "total_questions": exam.questions.count()
})
    

@api_view(['GET'])
@permission_classes([IsOrgMember])
def my_results(request):

    org = request.user.current_organisation

    attempts = ExamAttempt.objects.filter(
        user=request.user,
        exam__organisation=org,
        status__in=['completed', 'terminated']
    ).select_related('exam')

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

        serializer.save(
            created_by=self.request.user,
            organisation=self.request.user.current_organisation 
        )