from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=24, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(models.Model):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"

    ROLE_CHOICES = (
        (ADMIN, "Admin"),
        (MANAGER, "Manager"),
        (STAFF, "Staff"),
    )

    name = models.CharField(max_length=20, unique=True, choices=ROLE_CHOICES)
    description = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class UserRole(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_REVOKED = "revoked"

    ACTION_GRANT_ROLE = "grant_role"
    ACTION_REVOKE_ROLE = "revoke_role"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_REVOKED, "Revoked"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_memberships",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_memberships",
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__name", "user__username"]

    def __str__(self):
        return "%s / %s / %s" % (self.user.username, self.role.name, self.department.code)

    @property
    def role_name(self):
        return self.role.name

    @property
    def is_active_member(self):
        return self.status == self.STATUS_ACTIVE

    def can_access_department(self, department):
        if self.role_name == Role.ADMIN:
            return True
        return department_id(department) == self.department_id

    def can_manage_catalog(self):
        return self.role_name in (Role.ADMIN, Role.MANAGER)

    def can_delete_records(self):
        return self.role_name == Role.ADMIN

    def can_manage_bills(self):
        return self.role_name in (Role.ADMIN, Role.MANAGER)

    def can_manage_roles(self):
        return self.role_name == Role.ADMIN

    def can_view_stats(self):
        return self.role_name in (Role.ADMIN, Role.MANAGER, Role.STAFF)

    def transition(self, actor, target=None, action=None, payload=None):
        payload = payload or {}
        actor_membership = getattr(actor, "membership", None)
        if actor_membership is None or actor_membership.role_name != Role.ADMIN:
            raise PermissionDenied("Only admin can change role workflow.")

        transition_map = {
            (self.STATUS_ACTIVE, self.ACTION_GRANT_ROLE): self.STATUS_SUSPENDED,
            (self.STATUS_SUSPENDED, self.ACTION_REVOKE_ROLE): self.STATUS_REVOKED,
        }
        next_status = transition_map.get((self.status, action))
        if next_status is None:
            raise ValidationError("Illegal transition requested.")

        with transaction.atomic():
            if target is not None:
                self.role = target
            if payload.get("department") is not None:
                self.department = payload["department"]
            self.status = next_status
            self.approved_by = actor
            self.deleted_at = timezone.now() if next_status == self.STATUS_REVOKED else None
            self.save()
        return self


def department_id(department):
    if department is None:
        return None
    if hasattr(department, "pk"):
        return department.pk
    return department

