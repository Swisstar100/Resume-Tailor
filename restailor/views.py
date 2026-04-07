from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def homepage_view(request):
    return render(request, 'homepage.html')