import os
import logging
import bleach
from django.http import JsonResponse
from dotenv import find_dotenv, load_dotenv
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.contrib import messages
from .models import Application
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404, redirect
from .forms import ApplicationForm
from .utils.extraction import extract_text_from_pdf
from .tasks import generate_ai_resume_task, generate_student_feedback_task, process_application_task

# --- Fix #1: Whitelist for locked_sections to prevent prompt injection ---
ALLOWED_LOCKED_SECTIONS = {'skills', 'experience', 'projects'}

handler403 = 'applic.views.ratelimited_error'

@login_required(login_url='users:login')
def application_status(request):
    """Returns score + task status for all of the user's applications.
    Used by the board page to poll for score updates without a full reload."""
    apps = request.user.applications.values(
        'id', 'resume_task_status', 'old_skills'
    )
    data = {
        app['id']: {
            'status': app['resume_task_status'],
            'score':  app['old_skills'][3] if app['old_skills'] and len(app['old_skills']) > 3 else None,
        }
        for app in apps
    }
    return JsonResponse(data)

@login_required(login_url='users:login')
def application_task_status(request, app_id):
    application = get_object_or_404(Application, id=app_id, user=request.user)
    return JsonResponse({
        'resume_task_status':   application.resume_task_status,
        'feedback_task_status': application.feedback_task_status,
        'has_returned_resume':  bool(application.returned_resume),
        'has_resume_feedback':  bool(application.resume_feedback),
    })

def ratelimited_error(request, exception):
    if isinstance(exception, Ratelimited):
        return JsonResponse({'error': 'Too many submissions. Please wait before trying again.'}, status=429)

@login_required(login_url='users:login')
def board_view(request):
    applications = request.user.applications.all().order_by('-created_at')
    return render(request, "applic/board.html", {
        "applications": applications
    })

@login_required(login_url='users:login')
def application_view(request, app_id):
    application = get_object_or_404(Application, id=app_id, user=request.user)
    return render(request, 'applic/application.html', {
        'application': application
    })

@ratelimit(key='user', rate='6/h', method='POST', block=True)
@ratelimit(key='ip', rate='9/h', method='POST', block=True)
@login_required(login_url='users:login')
def create_application_view(request):
    user = request.user

    if user.applications.count() >= 50:
        messages.error(request, "You have reached the maximum number of applications.")
        return redirect('applications:board')

    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            
            app.uploaded_post = app.uploaded_post[:7000]
            file = request.FILES['uploaded_resume']
            extracted_text = extract_text_from_pdf(file)
            app.processed_resume = extracted_text[:7000]

            app.save()

            process_application_task.delay(app.id)

            messages.success(request, "Application created successfully.")
            return redirect('applications:board')
    else:
        form = ApplicationForm()

    return render(request, 'applic/create_application.html', {'form': form})


# --- Fix #4: Replaced @api_view with standard @login_required + @require_POST
#     so Django's built-in CSRF middleware is unambiguously enforced.
#     @require_POST also implicitly fixes #6 (GET triggering billable calls). ---
@ratelimit(key='user', rate='2/h', method='POST', block=True)
@ratelimit(key='ip', rate='3/h', method='POST', block=True)
@login_required(login_url='users:login')
@require_POST
def create_ai_application(request, app_id):
    application = get_object_or_404(Application, id=app_id, user=request.user)

    raw_sections = request.POST.getlist('locked_sections')
    locked_sections = [s for s in raw_sections if s in ALLOWED_LOCKED_SECTIONS]

    updated = (
        Application.objects
        .filter(pk=application.pk)
        .exclude(resume_task_status='processing')
        .update(resume_task_status='processing')
    )
    if not updated:
        messages.warning(request, "Optimization already in progress.")
        return redirect('applications:application', app_id=application.id)
    
    application.resume_task_status = 'processing'
    application.save()
    generate_ai_resume_task.delay(app_id, locked_sections) 
    messages.success(request, "Resume optimization started!")

    return redirect('applications:application', app_id=application.id)


# --- Fix #5: @require_POST prevents GET-triggered deletion ---
@login_required(login_url='users:login')
@require_POST
def delete_resume(request, app_id):
    app = get_object_or_404(Application, id=app_id, user=request.user)

    if app.uploaded_resume:
        app.uploaded_resume.delete(save=False)
        app.uploaded_resume = None
        app.save()

    return redirect('applications:board')


# --- Fix #6: @require_POST prevents GET-triggered billable AI calls ---
@login_required(login_url='users:login')
@require_POST
def student_improvements(request, app_id):
    application = get_object_or_404(Application, id=app_id, user=request.user)

    if not application.returned_processed_resume:
        messages.error(request, "Please optimize your resume before requesting feedback.")
        return redirect('applications:application', app_id=app_id)

    if application.resume_feedback:
        messages.warning(request, "Feedback has already been generated.")
        return redirect('applications:application', app_id=app_id)

    updated = (
        Application.objects
        .filter(pk=application.pk)
        .exclude(feedback_task_status='processing')
        .update(feedback_task_status='processing')
    )
    if not updated:
        messages.warning(request, "A task is already in progress.")
        return redirect('applications:application', app_id=app_id)
    
    application.feedback_task_status = 'processing'
    application.save()
    generate_student_feedback_task.delay(app_id)

    messages.success(request, "AI feedback generated successfully.")
    return redirect('applications:application', app_id=application.id)