from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Organisation, OrganisationMember
from django.contrib.auth import get_user_model
import uuid
from .models import OrganisationInvite
from django.utils.text import slugify

User = get_user_model()


# 1. Create Organisation
class CreateOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get("name")

        if not name:
            return Response(
                {"error": "Organisation name is required"},
                status=400
            )

        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while Organisation.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organisation.objects.create(
            name=name,
            slug=slug,
            owner=request.user
        )

        OrganisationMember.objects.create(
            organisation=org,
            user=request.user,
            role="owner"
        )

        request.user.current_organisation = org
        request.user.save()

        return Response({
            "status": "created",
            "slug": org.slug,
            "name": org.name,
            "plan": org.plan,
            "role": "owner"
        })
    

# 2. List my organisations
class MyOrganisationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            OrganisationMember.objects
            .filter(user=request.user, is_active=True)
            .select_related("organisation")
        )

        data = [
            {
                "name": m.organisation.name,
                "slug": m.organisation.slug,
                "role": m.role
            }
            for m in memberships
        ]

        return Response({
            "count": len(data),
            "organisations": data
        })


#  3. Switch organisation
class SwitchOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        membership = OrganisationMember.objects.filter(
            user=request.user,
            organisation__slug=slug
        ).first()

        if not membership:
            return Response({"error": "Not a member"}, status=403)

        request.user.current_organisation = membership.organisation
        request.user.save()

        return Response({
            "status": "switched",
            "slug": membership.organisation.slug,
            "name": membership.organisation.name,
            "plan": membership.organisation.plan,
            "role": membership.role
        })

#  4. Invite member 


class InviteMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        org = get_object_or_404(Organisation, slug=slug)

        # check admin access
        if not org.members.filter(
            user=request.user,
            role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)

        email = request.data.get("email")
        role = request.data.get("role", "candidate")
        expiry_days = request.data.get("expiry_days")

        if not email:
            return Response({"error": "email required"}, status=400)

        # handle expiry (admin controlled)
        expires_at = None
        if expiry_days:
            try:
                expiry_days = int(expiry_days)

                # safety limit
                if expiry_days < 1 or expiry_days > 30:
                    return Response(
                        {"error": "expiry_days must be between 1 and 30"},
                        status=400
                    )

                expires_at = now() + timedelta(days=expiry_days)

            except:
                return Response({"error": "Invalid expiry_days"}, status=400)

        # create invite
        invite = OrganisationInvite.objects.create(
            organisation=org,
            email=email,
            role=role,
            token=str(uuid.uuid4()),
            expires_at=expires_at
        )

        # check if user already exists
        user = User.objects.filter(email=email).first()

        if user:
            member, _ = OrganisationMember.objects.get_or_create(
                organisation=org,
                user=user,
                defaults={"role": role}
            )

            invite.accepted = True
            invite.save()

            return Response({
                "status": "user added directly",
                "org_slug": org.slug,
                "org_name": org.name,
                "org_plan": org.plan,
                "org_role": member.role
            })

        return Response({
            "status": "invite created",
            "invite_token": invite.token,
            "expires_at": invite.expires_at
        })
    

# 5. List members (admin only)
class OrganisationMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org = get_object_or_404(Organisation, slug=slug)

        if not org.members.filter(
            user=request.user,
            role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)

        members = org.members.select_related("user")

        data = [
            {
                "username": m.user.username,
                "email": m.user.email,
                "role": m.role
            }
            for m in members
        ]

        return Response(data)
    
class AcceptInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        invite = get_object_or_404(OrganisationInvite, token=token)

        if invite.accepted:
            return Response({"error": "Already accepted"}, status=400)

        # CHECKS MUST COME FIRST
        if invite.is_revoked:
            return Response({"error": "Invite revoked"}, status=400)

        if invite.expires_at and now() > invite.expires_at:
            return Response({"error": "Invite expired"}, status=400)

        # ONLY AFTER VALIDATION then create member
        member, _ = OrganisationMember.objects.get_or_create(
            organisation=invite.organisation,
            user=request.user,
            defaults={"role": invite.role}
        )

        invite.accepted = True
        invite.save()

        # set active organisation
        request.user.current_organisation = invite.organisation
        request.user.save()

        return Response({
            "status": "joined",
            "org_slug": invite.organisation.slug,
            "org_name": invite.organisation.name,
            "org_plan": invite.organisation.plan,
            "org_role": member.role
        })