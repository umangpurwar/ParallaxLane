from django.contrib import admin
from .models import Organisation, OrganisationMember, OrganisationInvite, Coupon


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


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'plan', 'active', 'used_count', 'max_uses', 'expires_at', 'created_at']
    list_filter = ['plan', 'active']
    search_fields = ['code']
    readonly_fields = ['used_count', 'created_at']