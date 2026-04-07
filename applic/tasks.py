from celery import shared_task
import anthropic
import os
import uuid
import logging
from dotenv import find_dotenv, load_dotenv
from .models import Application
from .utils.scoring2 import get_skill_experience_info, html_to_text, normalize_text
from .utils.sanitize import _sanitize_ai_html
from .utils.pdf import resume_to_pdf
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)
User = get_user_model()
load_dotenv(find_dotenv())
_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not _ANTHROPIC_API_KEY:
    raise ImproperlyConfigured(
        "ANTHROPIC_API_KEY environment variable is not set."
    )


@shared_task(bind=True, max_retries=2)
def generate_ai_resume_task(self, app_id, locked_sections):
    try:
        application = Application.objects.get(id=app_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found in generate_ai_resume_task", app_id)
        return

    user_resume = (application.processed_resume or "")[:7000]
    job_post = (application.uploaded_post or "")[:7000]
    locked_text = ", ".join(locked_sections) if locked_sections else "No locked sections, you may edit any section of the resume."

    client = anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY)

    system_prompt = f"""
You are a professional resume writer optimizing resumes for ATS systems.

Your task:
- Rewrite the resume to better match the job posting
- Improve clarity, impact, and keyword alignment
- Only rephrase, reorganize, and carefully expand existing content

### Locked Sections: Under no circumstance will you edit any of the contents in the following section(s):
{locked_text}



Optimization Strategy:
- Prioritize emphasizing existing relevant skills
- Incorporate relevant keywords from the job description ONLY when truthful
- Strengthen bullet points using strong action verbs without exaggerating responsibility

Existing Relevant Skills:
{application.matched_skills}

### COSINE SIMILARITY TARGETS:
Each item is a mapping of (job responsibility, resume bullet, similarity score):
{application.old_experience_matches}

Each resume bullet is paired with the MOST relevant job responsibility.
You must optimize each bullet specifically for its paired job responsibility.

### BULLET OPTIMIZATION REQUIREMENTS:
- For EACH resume bullet, rewrite it to more closely match its corresponding job responsibility
- Mirror the language, structure, and terminology of the job responsibility ONLY when it does not change the original meaning
- Maintain the original meaning, scope, and technologies used
- Improve semantic similarity WITHOUT introducing new concepts

### BULLET-LEVEL CONSTRAINTS:
- Every bullet must be rewritten (no unchanged bullets)
- Each rewritten bullet must align more closely with a specific job responsibility within the limits of the original content
- Prefer action verbs and phrasing used in the job description ONLY if accurate
- Avoid generic phrasing; increase specificity where supported
- Do not introduce new responsibilities, tools, or technologies not present in the original bullet

### STRUCTURAL CONSISTENCY:
- Preserve the number of bullet points for each role or project
- Do not remove or merge bullet points
- Do not create new bullet points
- Every role or position MUST have at least one bullet point

### GROUNDING & TRUTH CONSTRAINT (HIGHEST PRIORITY):

All rewritten bullets MUST be strictly grounded in the original bullet.

Allowed transformations:
- Rewording for clarity or impact
- Reordering phrasing
- Substituting synonyms (e.g., "built" → "developed")
- Adding detail ONLY if it is explicitly stated or unambiguously implied

NOT allowed under any circumstance:
- Adding new tools, technologies, or methodologies not explicitly present
- Upgrading level of responsibility (e.g., "assisted" → "led", "worked on" → "owned")
- Changing scope (e.g., feature → system, component → platform)
- Inferring metrics, impact, scale, or outcomes not stated
- Claiming ownership of work not clearly indicated
- Combining multiple experiences into one

If a job requirement contains a concept not present in the bullet:
→ DO NOT add it
→ Instead, rewrite the bullet to be as closely related as possible without introducing new information

If insufficient information exists:
→ Keep the bullet conservative and accurate
→ Prefer under-claiming over over-claiming
→ When in doubt, preserve the original meaning closely

### EXPERIENCE ENHANCEMENT RULES:
- Expand bullets ONLY when details are explicitly stated or clearly implied
- Do NOT infer missing technologies, tools, or responsibilities
- Increase clarity and precision without adding new information
- Avoid overly short bullet points while staying truthful

### PRIORITIZATION:
- Prioritize improving bullets that have lower cosine similarity scores first
- For low similarity bullets, improve clarity and alignment WITHOUT adding new concepts
- For high similarity bullets, refine wording without major changes
- Never force alignment at the cost of accuracy

### KEYWORD ALIGNMENT:
- You may incorporate terminology from the job description ONLY if the underlying skill or action already exists in the original bullet
- Terminology substitution must NOT change the meaning of the work performed

### TRACEABILITY REQUIREMENT:
- Each rewritten bullet must map directly to its original bullet
- Do NOT merge, split, or cross-reference bullets

### VALIDATION STEP (MANDATORY BEFORE OUTPUT):
For EACH rewritten bullet, verify:
1. Does this introduce any new tool, technology, or responsibility not in the original?
2. Does this exaggerate ownership, impact, or scope?
3. Can every part of this bullet be traced back to the original?

If ANY answer is "yes":
→ Revise the bullet until it is strictly grounded in the original

Do NOT output bullets that fail this validation.

### CRITICAL RULES:
- If a missing skill is not present in the resume, DO NOT invent it
- If a section is locked, do NOT change wording, structure, or content
- You may improve other sections freely within constraints
- Ensure relevant skills appear in both Skills and Experience/Project sections ONLY if already present
- Do not remove relevant technical details from the original resume

Output Requirements:
- Sections: Education, Skills, Experience (if experience is not relevant to job, place below projects), Projects, Volunteer Experience
- Organize skills into Programming Languages, Tools, and Frameworks
- Output ONLY valid HTML (no markdown, no code fences)
- Do not include <html>, <head>, <body>, or <style> tags — only the inner content

### REQUIRED STRUCTURE:

For the header:
<div class="resume-header">
  <h1>Full Name</h1>
  <p class="contact">email · phone · location · LinkedIn · GitHub</p>
</div>

For each section:
<div class="section">
  <h2>Section Title</h2>
  <div class="entry">
    <div class="entry-header">
      <span class="entry-title">Title here</span>
      <span class="entry-date">Date here</span>
    </div>
    <div class="entry-sub">Subtitle or tech stack</div>
    <ul>
      <li>Bullet point</li>
    </ul>
  </div>
</div>

For projects:
- Put the tech stack in:
<span class="tech">| Django · Python · ...</span>

STRICT FORMATTING RULES:
- Every entry with a date MUST use this exact structure, no exceptions:
    <div class="entry-header">
      <span class="entry-title">Title here</span>
      <span class="entry-date">Date here</span>
    </div>
- This applies to ALL sections including Volunteer Experience
- NEVER output a section with an entry that has no <ul> and no <li>
- Do not use em dashes
- Do not add inline styles
- Keep resume to ~500 words, 1 full page
"""

    user_message = f"""
<USER_RESUME>
{user_resume}
</USER_RESUME>

<JOB_POST>
{job_post}
</JOB_POST>
"""
    try:
        anthropic_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system = system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        html_ai_resume = anthropic_response.content[0].text
    except Exception as exc:
        logger.exception("Anthropic API error in generate_ai_resume_task for app_id=%s", app_id)
        application.resume_task_status = 'failed'
        application.save()
        raise self.retry(exc=exc, countdown=5)

    html_ai_resume = _sanitize_ai_html(html_ai_resume)
    filename = f"resume_{uuid.uuid4().hex}.pdf"
    pdf_path = None

    try:
        pdf_path = resume_to_pdf(html_ai_resume, filename)

        with open(pdf_path, 'rb') as f:
            application.returned_resume.save(filename, ContentFile(f.read()), save=False)

        extracted_text = html_to_text(html_ai_resume)
        extracted_text = normalize_text(extracted_text)
        application.returned_processed_resume = extracted_text

        score_info = get_skill_experience_info(extracted_text[:7000], application.uploaded_post)
        application.new_skills = [score_info["skill_score"], score_info["experience_score"], 100, round(score_info["skill_score"] * .6 + score_info["experience_score"] * .4, 2)]
        application.new_experience_matches = [
            {
                "job":    str(match["job"]),
                "resume": str(match["resume"]),
                "score":  float(match["score"]),
            }
            for match in score_info["detailed_experience_matches"]
        ]

        application.resume_task_status = 'done'
        application.save()

    except Exception:
        logger.exception("PDF generation/save error in generate_ai_resume_task for app_id=%s", app_id)
        raise

    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning("Could not delete temp PDF: %s", pdf_path)


@shared_task(bind=True, max_retries=2)
def generate_student_feedback_task(self, app_id):
    try:
        application = Application.objects.get(id=app_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found in generate_student_feedback_task", app_id)
        return

    resume_text = (application.returned_processed_resume or "")[:7000]

    system_prompt = f"""
You are a professional career coach for computer science students seeking internships.

Your task:
- Review the following resume content.
- Provide constructive feedback focused on **skills, projects, work experience, and overall readiness** for internship roles.
- Structure your feedback under these headings:

1. **Strengths** - Highlight the candidate's strong skills, technologies, and successful projects.
2. **Areas to Improve** - Point out missing skills, weak or underdeveloped areas, or gaps in experience.
3. **Project Feedback** - Evaluate the projects' relevance, impact, and completeness.
4. **Recommendations** - Suggest specific steps or focus areas the candidate can take to improve competitiveness for internships.

- Keep feedback approximately **200 words**.
- Do **not** comment on formatting, grammar, or layout—focus solely on content, skills, and experience.
- Use professional, clear, and encouraging language.
"""

    user_message = f"""
<USER_RESUME>
{resume_text}
</USER_RESUME>
"""
    client = anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY)
    try:
        anthropic_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system = system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        feedback = anthropic_response.content[0].text
    except Exception as exc:
        logger.exception("Anthropic API error in generate_student_feedback_task for app_id=%s", app_id)
        application.feedback_task_status = 'failed'
        application.save()
        raise self.retry(exc=exc, countdown=5)

    sanitized_feedback = _sanitize_ai_html(feedback)
    application.resume_feedback = sanitized_feedback
    application.feedback_task_status = 'done'
    application.save()

@shared_task(bind=True, max_retries=2)
def process_application_task(self, app_id):
    try:
        application = Application.objects.get(id=app_id)
    except Application.DoesNotExist:
        logger.error("Application %s not found in process_application_task", app_id)
        return

    try:
        score_info = get_skill_experience_info(application.processed_resume[:7000], application.uploaded_post)
        application.old_skills = [score_info["skill_score"], score_info["experience_score"], 100, round(score_info["skill_score"] * .6 + score_info["experience_score"] * .4, 2)]
        application.matched_skills = score_info["matched_skills"]
        application.old_experience_matches = [
            {
                "job":    str(match["job"]),
                "resume": str(match["resume"]),
                "score":  float(match["score"]),
            }
            for match in score_info["detailed_experience_matches"]
        ]
        application.save()

    except Exception as exc:
        logger.exception("Scoring error in process_application_task for app_id=%s", app_id)
        raise self.retry(exc=exc, countdown=5)