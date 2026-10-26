from django import forms
from django.utils import timezone

from .models import Questionnaire, Submission


class HRReportFilterForm(forms.Form):
    questionnaire = forms.ModelChoiceField(
        label="Анкета",
        queryset=Questionnaire.objects.all(),
        empty_label="Выберите анкету",
    )

    period_start = forms.DateField(
        label="Начало периода",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )

    period_end = forms.DateField(
        label="Конец периода",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )

    department = forms.ChoiceField(
        label="Отдел",
        required=False,
        choices=(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        departments = (
            Submission.objects
            .filter(expires_at__gt=timezone.localdate())
            .exclude(department="")
            .order_by("department")
            .values_list("department", flat=True)
            .distinct()
        )

        self.fields["department"].choices = [
            ("", "Все отделы"),
            *[(name, name) for name in departments],
        ]

    def clean(self):
        cleaned_data = super().clean()

        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")

        if (
            period_start is not None
            and period_end is not None
            and period_start > period_end
        ):
            self.add_error(
                "period_end",
                "Конец периода не может быть раньше начала.",
            )

        return cleaned_data