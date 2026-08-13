from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from io import StringIO

from .forms import MatchResultUploadForm
from .services.match_result_updater import update_match_results


@staff_member_required
def match_result_update(request):

    if request.method == "POST":

        form = MatchResultUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            csv_file = form.cleaned_data["csv_file"]

            try:
                # UploadedFile is binary.
                # Convert it to text for csv.DictReader.
                file_content = csv_file.read().decode("utf-8-sig")

                text_file = StringIO(file_content)

                result = update_match_results(
                    text_file
                )

                if result["updated"]:
                    messages.success(
                        request,
                        f"Updated matches: {result['updated']}"
                    )

                if result["not_found"]:
                    messages.warning(
                        request,
                        f"Matches not found: {result['not_found']}"
                    )

                if result["errors"]:
                    messages.error(
                        request,
                        f"Errors: {result['errors']}"
                    )

                request.session[
                    "match_update_details"
                ] = result["details"]

                return redirect(request.path)

            except UnicodeDecodeError:
                messages.error(
                    request,
                    "Could not read the CSV file. "
                    "Please make sure it is saved as UTF-8 CSV."
                )

    else:

        form = MatchResultUploadForm()

    details = request.session.pop(
        "match_update_details",
        []
    )

    return render(
        request,
        "admin/core/match_result_update.html",
        {
            "form": form,
            "details": details,
        }
    )