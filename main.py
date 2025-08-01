import os
import io
import zipfile
from flask import Flask, request, render_template_string, send_file
import utils
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# HTML Template (inline)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ATS Resume Checker</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: auto; padding: 20px; }
        h1, h2 { color: #333; }
        form { margin-bottom: 20px; }
        .feedback { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
        .passed { background: #e1f5e1; }
        .failed { background: #fce4e4; }
    </style>
</head>
<body>
    <h1>ATS Resume Checker</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>Job Description:</label><br>
        <textarea name="job_desc" rows="6" cols="70">{{ job_desc or '' }}</textarea><br><br>

        <label>Min Experience:</label>
        <input type="number" name="min_exp" value="{{ min_exp or 1 }}"><br><br>

        <label>Max Experience:</label>
        <input type="number" name="max_exp" value="{{ max_exp or 3 }}"><br><br>

        <label>ATS Score Criteria:</label>
        <input type="number" name="ats_criteria" value="{{ ats_criteria or 75 }}"><br><br>

        <label>Upload Resumes:</label>
        <input type="file" name="resumes" multiple><br><br>

        <button type="submit">Process Resumes</button>
    </form>

    {% if error %}
        <div style="color:red; margin-bottom:20px;">{{ error }}</div>
    {% endif %}

    {% if results %}
        <h2>Results</h2>
        {% for result in results %}
            <div class="feedback {% if result.passed %}passed{% else %}failed{% endif %}">
                <b>{{ result.name }}</b><br>
                ATS Score: {{ result.score }}%<br>
                <i>{{ result.feedback }}</i>
            </div>
        {% endfor %}

        {% if zip_ready %}
            <form method="GET" action="/download">
                <button type="submit">Download Shortlisted Resumes as ZIP</button>
            </form>
        {% endif %}
    {% endif %}
</body>
</html>
"""

shortlisted_resumes = []

@app.route("/", methods=["GET", "POST"])
def index():
    global shortlisted_resumes
    results = []
    zip_ready = False
    error = None

    if request.method == "POST":
        job_desc = request.form.get("job_desc", "")
        min_exp = int(request.form.get("min_exp", 1))
        max_exp = int(request.form.get("max_exp", 3))
        ats_criteria = int(request.form.get("ats_criteria", 75))
        uploaded_files = request.files.getlist("resumes")

        if not job_desc.strip():
            error = "Please provide a job description before processing resumes."
            return render_template_string(HTML_TEMPLATE, results=None, error=error)

        if len(uploaded_files) == 0:
            error = "Please upload at least one resume to proceed."
            return render_template_string(HTML_TEMPLATE, results=None, error=error)

        shortlisted_resumes = []
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.filename
            pdf_content = utils.file_to_text(uploaded_file)

            if not pdf_content:
                results.append({
                    "name": file_name,
                    "score": 0,
                    "feedback": "Rejected: Empty or unreadable resume.",
                    "passed": False
                })
                continue

            prompt = utils.get_prompt_with_feedback(pdf_content, job_desc, min_exp, max_exp)
            ats_score, feedback = utils.get_ats_score_and_feedback(prompt, file_name)

            if ats_score < ats_criteria:
                results.append({
                    "name": file_name,
                    "score": ats_score,
                    "feedback": f"Rejected: ATS score {ats_score}% is below threshold.",
                    "passed": False
                })
                continue

            results.append({
                "name": file_name,
                "score": ats_score,
                "feedback": f"Accepted: {feedback}",
                "passed": True
            })

            shortlisted_resumes.append({"name": file_name, "file": uploaded_file})

        if len(shortlisted_resumes) > 0:
            zip_ready = True

        return render_template_string(
            HTML_TEMPLATE,
            results=results,
            zip_ready=zip_ready,
            job_desc=job_desc,
            min_exp=min_exp,
            max_exp=max_exp,
            ats_criteria=ats_criteria
        )

    return render_template_string(HTML_TEMPLATE, results=None)

@app.route("/download", methods=["GET"])
def download_zip():
    global shortlisted_resumes
    if len(shortlisted_resumes) == 0:
        return render_template_string(HTML_TEMPLATE, results=None, error="No shortlisted resumes to download.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for res in shortlisted_resumes:
            res["file"].seek(0)
            zipf.writestr(res["name"], res["file"].read())
    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="shortlisted-resumes.zip"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
