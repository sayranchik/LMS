from django import forms

from .models import Assignment, Submission


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ("title", "description", "due_date", "max_score")
        widgets = {"due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ("text", "file")
        widgets = {"text": forms.Textarea(attrs={"rows": 5})}

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("text") and not cleaned.get("file") and not (self.instance and self.instance.file):
            raise forms.ValidationError("Додайте текст відповіді або прикріпіть файл.")
        return cleaned


class GradeForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ("score", "feedback")
        widgets = {"feedback": forms.Textarea(attrs={"rows": 4})}
