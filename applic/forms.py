from django import forms
from .models import Application

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['uploaded_resume', 'uploaded_post']

    def clean_uploaded_resume(self):
        file = self.cleaned_data.get('uploaded_resume')

        if not file:
            raise forms.ValidationError("No file uploaded.")

        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 5MB.")

        header = file.read(5)
        file.seek(0)
        if header != b'%PDF-':
            raise forms.ValidationError("Invalid file. Please upload a valid PDF.")

        return file