from django.contrib import admin
from .models import Organisation, OrganisationMember, OrganisationInvite


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'owner', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active']
    search_fields = ['name', 'slug']


@admin.register(OrganisationMember)
class OrganisationMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'organisation', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active']


@admin.register(OrganisationInvite)
class OrganisationInviteAdmin(admin.ModelAdmin):
    list_display = ['email', 'organisation', 'role', 'accepted', 'is_revoked', 'expires_at']
    list_filter = ['accepted', 'is_revoked']