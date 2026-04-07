import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator

class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    uploaded_resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    processed_resume = models.TextField(validators=[MaxLengthValidator(7000)])
    uploaded_post = models.TextField(null=True, blank=True, validators=[MaxLengthValidator(7000)])
    returned_resume = models.FileField(upload_to='generated_resumes/', null=True, blank=True)
    returned_processed_resume = models.TextField(null=True, blank=True)
    resume_feedback = models.TextField(null=True, blank=True)
    old_skills = models.JSONField(default=list, blank=True) # From original processed resume
    new_skills = models.JSONField(default=list, blank=True) # From AI rewrite
    matched_skills = models.JSONField(default=list, blank=True)
    old_experience_matches = models.JSONField(default=list, blank=True)
    new_experience_matches = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resume_task_status = models.CharField(
        max_length=20,
        choices=[('idle', 'Idle'), ('processing', 'Processing'), ('done', 'Done'), ('failed', 'Failed')],
        default='idle'
    )
    feedback_task_status = models.CharField(
        max_length=20,
        choices=[('idle', 'Idle'), ('processing', 'Processing'), ('done', 'Done'), ('failed', 'Failed')],
        default='idle'
    )
