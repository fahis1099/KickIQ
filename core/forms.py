from django import forms


class MatchResultUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Match Results CSV",
        help_text=(
            "Upload the same match CSV format used "
            "for weekly match updates."
        )
    )