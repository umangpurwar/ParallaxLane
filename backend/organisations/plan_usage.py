from exams.models import Exam
from organisations.plan_features import get_plan_features
from organisations.models import OrganisationMember


def get_organisation_usage(org):
    features = get_plan_features(org)

    exam_count = Exam.objects.filter(organisation=org).count()
    members = OrganisationMember.objects.filter(organisation=org, is_active=True)

    return {
        "plan": org.plan,
        "plan_label": org.plan.upper(),
        "features": {
            "max_questions_per_exam": features["max_questions"],
            "allowed_question_types": features["allowed_question_types"],
            "image_questions": features["image_questions"],
            "file_upload": features["file_upload"],
        },
        "usage": {
            "exams_created": exam_count,
            "max_exams": org.max_exams,
            "candidates": members.filter(role=OrganisationMember.ROLE_CANDIDATE).count(),
            "max_candidates": org.max_candidates,
            "admins": members.filter(role=OrganisationMember.ROLE_ADMIN).count(),
            "max_admins": org.max_admins,
            "invigilators": members.filter(role=OrganisationMember.ROLE_INVIGILATOR).count(),
            "max_invigilators": org.max_invigilators,
            "proctoring_enabled": org.proctoring_enabled,
        },
    }
