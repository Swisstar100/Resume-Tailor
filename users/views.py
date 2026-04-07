from django.shortcuts import render, redirect 
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm 
from django.contrib.auth import login, logout
from django.contrib.auth.models import User

def register_view(request):
    if request.method == "POST": 
        form = UserCreationForm(request.POST) 
        email = request.POST.get("email")  # get the email from the template
        if form.is_valid(): 
            user = form.save(commit=False)
            user.email = email  # save email to the user
            user.save()
            login(request, user)
            return redirect("applications:board")
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", { "form": form })

def login_view(request): 
    if request.method == "POST": 
        form = AuthenticationForm(data=request.POST)
        if form.is_valid(): 
            login(request, form.get_user())
            return redirect("applications:board")
    else: 
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form": form })

def logout_view(request):
    if request.method == "POST": 
        logout(request) 
        return redirect("users:login")