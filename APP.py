from flask import Flask, request, render_template_string, Markup
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

app = Flask(__name__)

# =========================
# HTML TEMPLATE
# =========================
HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Study Planner</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #c9e6ff, #f9f0ff);
            margin: 0;
            padding: 0;
        }
        h1 { text-align: center; color: #0056b3; margin-top: 30px; }
        form, .result {
            background: white; padding: 25px; border-radius: 15px;
            max-width: 900px; margin: 30px auto;
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        input, textarea {
            width: 100%; padding: 10px; margin: 6px 0;
            border: 1px solid #ddd; border-radius: 8px;
        }
        input[type="submit"] {
            background: linear-gradient(90deg, #007BFF, #00c6ff);
            color: white; border: none; font-size: 1.1em;
            padding: 12px; border-radius: 8px; cursor: pointer;
            margin-top: 10px;
        }
        input[type="submit"]:hover {
            background: linear-gradient(90deg, #0056b3, #0095cc);
        }
        .section { background: #eef7ff; border-left: 5px solid #007BFF;
                   padding: 10px; margin-top: 10px; border-radius: 8px; }
        table {
            width: 100%; border-collapse: collapse; margin-top: 10px;
        }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background: #007BFF; color: white; }
        tr:nth-child(even) { background: #f9f9f9; }
        .chart-container { text-align: center; margin-top: 20px; }
        img { max-width: 100%; height: auto; border-radius: 10px; }
        .error { color: red; font-weight: bold; margin-top: 10px; text-align: center; }
    </style>
</head>
<body>
<h1>📘 AI Study Planner</h1>

<form method="POST">
    <label>📚 Subjects (comma-separated):</label>
    <input type="text" name="subjects" placeholder="e.g. Math, Physics, History, English" required>

    <label>📝 Current Scores (comma-separated):</label>
    <input type="text" name="scores" placeholder="e.g. 70, 80, 65, 72" required>

    <label>🎯 Desired Scores (comma-separated):</label>
    <input type="text" name="desired_scores" placeholder="e.g. 90, 85, 80, 88" required>

    <label>📅 Test Dates (YYYY-MM-DD, comma-separated):</label>
    <input type="text" name="dates" placeholder="e.g. 2025-11-10, 2025-12-05, 2025-12-20, 2026-01-10" required>

    <label>⏳ Total Study Hours Available:</label>
    <input type="number" step="0.1" name="total_hours" required>

    <input type="submit" value="✨ Generate My Smart Plan ✨">
</form>

{% if error %}
<div class="result error">{{ error }}</div>
{% endif %}

{% if result %}
<div class="result">
    <h2>📅 Study Hours Allocation</h2>
    <div class="section">{{ result['schedule'] | safe }}</div>

    <div class="chart-container">
        <h2>📊 Weekly Study Plan per Subject</h2>
        <img src="data:image/png;base64,{{ result['weekly_chart'] }}">
    </div>
</div>
{% endif %}
</body>
</html>
"""

# =========================
# BACKEND LOGIC
# =========================
def create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours):
    today = datetime.today()
    urgency = [(datetime.strptime(d, "%Y-%m-%d") - today).days for d in test_dates]
    urgency = [max(u, 1) for u in urgency]
    improvement_needed = [max(0, d - s) for s, d in zip(scores, desired_scores)]

    # Weight each subject based on improvement and urgency
    weights = [imp / urg for imp, urg in zip(improvement_needed, urgency)]
    total_weight = sum(weights) if sum(weights) > 0 else 1

    # Allocate total available hours proportionally
    allocations = [(w / total_weight) * total_hours for w in weights]
    return {subj: round(hours, 1) for subj, hours in zip(subjects, allocations)}

def generate_weekly_chart(schedule, subjects, test_dates):
    today = datetime.today()
    max_weeks = max([(datetime.strptime(d, "%Y-%m-%d") - today).days // 7 + 1 for d in test_dates])

    fig, ax = plt.subplots(figsize=(10, 6))
    # Use larger colormap if >10 subjects
    cmap = plt.cm.get_cmap('tab20', len(subjects))
    colors = [cmap(i) for i in range(len(subjects))]

    for i, subj in enumerate(subjects):
        test_date = datetime.strptime(test_dates[i], "%Y-%m-%d")
        weeks_until = max(1, (test_date - today).days // 7 + 1)
        weekly_hours = schedule[subj] / weeks_until

        weeks = np.arange(1, max_weeks + 1)
        hours = [weekly_hours if w <= weeks_until else 0 for w in weeks]

        ax.bar(weeks - 0.4 + i*(0.8/len(subjects)), hours, width=0.8/len(subjects),
               color=colors[i], label=subj)

    ax.set_xlabel("Weeks from Now")
    ax.set_ylabel("Study Hours per Week")
    ax.set_title("Weekly Study Plan per Subject")
    ax.legend(ncol=2, fontsize=8)
    ax.set_xticks(range(1, max_weeks + 1))
    ax.set_xticklabels([f"Week {i}" for i in range(1, max_weeks + 1)])
    plt.tight_layout()

    # Convert chart to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_b64

# =========================
# MAIN ROUTE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        try:
            subjects = [s.strip() for s in request.form["subjects"].split(",") if s.strip()]
            scores = [int(s) for s in request.form["scores"].split(",") if s.strip()]
            desired_scores = [int(s) for s in request.form["desired_scores"].split(",") if s.strip()]
            test_dates = [s.strip() for s in request.form["dates"].split(",") if s.strip()]
            total_hours = float(request.form["total_hours"])

            # Input validation
            if not (len(subjects) == len(scores) == len(desired_scores) == len(test_dates)):
                error = (
                    f"⚠️ Please ensure the number of subjects, scores, desired scores, "
                    f"and test dates all match.<br><br>"
                    f"You entered {len(subjects)} subjects, {len(scores)} scores, "
                    f"{len(desired_scores)} desired scores, and {len(test_dates)} dates."
                )
                return render_template_string(HTML_FORM, error=Markup(error))

            # Create schedule and chart
            schedule = create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours)
            weekly_chart = generate_weekly_chart(schedule, subjects, test_dates)

            # Build schedule table
            schedule_rows = "".join(
                [f"<tr><td>{s}</td><td>{h} hrs</td></tr>" for s, h in schedule.items()]
            )
            schedule_html = f"<table><tr><th>Subject</th><th>Allocated Study Hours</th></tr>{schedule_rows}</table>"

            result = {"schedule": Markup(schedule_html), "weekly_chart": weekly_chart}

        except Exception as e:
            error = f"⚠️ Invalid input: {str(e)}"

    return render_template_string(HTML_FORM, result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)
