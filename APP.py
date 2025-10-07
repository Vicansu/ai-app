from flask import Flask, request, render_template_string, Markup
from datetime import datetime
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
    <title>AI Study Planner Dashboard</title>
    <style>
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #d7e9ff, #f8e9ff);
            margin: 0; padding: 0; color: #222;
        }
        h1 {
            text-align: center;
            color: #0056b3;
            padding: 25px;
            background: rgba(255,255,255,0.9);
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        form, .result {
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 1000px;
            margin: 30px auto;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        label {
            font-weight: 600;
            margin-top: 15px;
            display: block;
        }
        input {
            width: 100%;
            padding: 12px;
            margin-top: 5px;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-sizing: border-box;
            font-size: 0.95em;
        }
        input[type="submit"] {
            background: linear-gradient(90deg, #007BFF, #00b8ff);
            color: white;
            font-weight: bold;
            font-size: 1.1em;
            border: none;
            border-radius: 8px;
            padding: 14px;
            margin-top: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        input[type="submit"]:hover {
            transform: scale(1.03);
            background: linear-gradient(90deg, #0056b3, #00a0e0);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            border: 1px solid #e0e0e0;
            padding: 10px;
            text-align: center;
            font-size: 0.95em;
        }
        th {
            background-color: #007BFF;
            color: white;
            letter-spacing: 0.03em;
        }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .chart-container {
            text-align: center;
            margin-top: 25px;
        }
        img {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 5px 10px rgba(0,0,0,0.15);
            margin-bottom: 20px;
        }
        .card {
            background: linear-gradient(145deg, #f9fbff, #ffffff);
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 12px;
            margin-top: 25px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }
        .summary-item {
            background: #eef6ff;
            border-left: 5px solid #007BFF;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
        }
        .error { color: red; text-align: center; font-weight: bold; margin-top: 15px; }
    </style>
</head>
<body>

<h1>📘 AI Study Planner Dashboard</h1>

<form method="POST">
    <label>📚 Subjects (comma-separated):</label>
    <input type="text" name="subjects" placeholder="e.g. Math, Physics, History" required>

    <label>📝 Current Scores (comma-separated):</label>
    <input type="text" name="scores" placeholder="e.g. 70, 85, 65" required>

    <label>🎯 Desired Scores (comma-separated):</label>
    <input type="text" name="desired_scores" placeholder="e.g. 90, 95, 80" required>

    <label>📅 Test Dates (YYYY-MM-DD, comma-separated):</label>
    <input type="text" name="dates" placeholder="e.g. 2025-11-10, 2025-12-05, 2026-01-15" required>

    <label>⏳ Total Study Hours Available:</label>
    <input type="number" step="0.1" name="total_hours" placeholder="e.g. 120" required>

    <input type="submit" value="✨ Generate My Study Dashboard ✨">
</form>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

{% if result %}
<div class="result">
    <div class="card">
        <h2>📅 Allocated Study Hours by Subject</h2>
        {{ result['schedule'] | safe }}
    </div>

    <div class="card chart-container">
        <h2>📊 Weekly Study Allocation</h2>
        <img src="data:image/png;base64,{{ result['weekly_chart'] }}" alt="Weekly Study Chart">
    </div>

    <div class="card chart-container">
        <h2>📈 Focus & Urgency Balance</h2>
        <img src="data:image/png;base64,{{ result['weight_chart'] }}" alt="Weight Chart">
    </div>

    <div class="card chart-container">
        <h2>📆 Cumulative Study Progress Projection</h2>
        <img src="data:image/png;base64,{{ result['progress_chart'] }}" alt="Progress Chart">
    </div>

    <div class="card">
        <h2>🧩 Summary</h2>
        <div class="summary">
            <div class="summary-item">Total Subjects: {{ result['total_subjects'] }}</div>
            <div class="summary-item">Total Study Hours: {{ result['total_hours'] }}</div>
            <div class="summary-item">Closest Exam: {{ result['closest_exam'] }}</div>
            <div class="summary-item">Avg. Hours/Subject: {{ result['avg_hours'] }}</div>
        </div>
    </div>
</div>
{% endif %}
</body>
</html>
"""

# =========================
# LOGIC
# =========================
def create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours):
    today = datetime.today()
    urgency = [(datetime.strptime(d, "%Y-%m-%d") - today).days for d in test_dates]
    urgency = [max(u, 1) for u in urgency]
    improvement_needed = [max(0, d - s) for s, d in zip(scores, desired_scores)]
    weights = [imp / urg for imp, urg in zip(improvement_needed, urgency)]
    total_weight = sum(weights) if sum(weights) > 0 else 1
    allocations = [(w / total_weight) * total_hours for w in weights]
    return {subj: round(hours, 1) for subj, hours in zip(subjects, allocations)}, weights, urgency

def generate_weekly_chart(schedule, subjects, test_dates):
    today = datetime.today()
    max_weeks = max([(datetime.strptime(d, "%Y-%m-%d") - today).days // 7 + 1 for d in test_dates])

    fig, ax = plt.subplots(figsize=(10, 6))
    cmap = plt.cm.get_cmap('tab20', len(subjects))
    colors = [cmap(i) for i in range(len(subjects))]

    for i, subj in enumerate(subjects):
        test_date = datetime.strptime(test_dates[i], "%Y-%m-%d")
        weeks_until = max(1, (test_date - today).days // 7 + 1)
        weekly_hours = schedule[subj] / weeks_until
        weeks = np.arange(1, max_weeks + 1)
        hours = [weekly_hours if w <= weeks_until else 0 for w in weeks]
        ax.bar(weeks - 0.4 + i * (0.8 / len(subjects)), hours, width=0.8 / len(subjects),
               color=colors[i], label=subj)

    ax.set_xlabel("Weeks from Now")
    ax.set_ylabel("Study Hours per Week")
    ax.set_title("Weekly Study Allocation per Subject")
    ax.legend(ncol=2, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return chart_b64

def generate_weight_chart(subjects, weights, urgency):
    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(subjects))
    ax.bar(x - 0.2, weights, width=0.4, label='Study Weight', color='#007BFF')
    ax.bar(x + 0.2, urgency, width=0.4, label='Urgency (days left)', color='#FFB84C')
    ax.set_xticks(x)
    ax.set_xticklabels(subjects, rotation=30, ha='right')
    ax.set_title("Subject Focus vs Urgency Balance")
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img_b64

def generate_progress_chart(schedule):
    subjects = list(schedule.keys())
    hours = list(schedule.values())
    cumulative = np.cumsum(hours)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(subjects, cumulative, marker='o', color='#28a745', linewidth=2)
    ax.set_title("Cumulative Study Progress Projection")
    ax.set_xlabel("Subjects")
    ax.set_ylabel("Cumulative Hours")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return chart_b64

# =========================
# ROUTE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        try:
            subjects = [s.strip() for s in request.form["subjects"].split(",") if s.strip()]
            scores = [int(s) for s in request.form["scores"].split(",")]
            desired_scores = [int(s) for s in request.form["desired_scores"].split(",")]
            test_dates = [s.strip() for s in request.form["dates"].split(",")]
            total_hours = float(request.form["total_hours"])

            if not (len(subjects) == len(scores) == len(desired_scores) == len(test_dates)):
                raise ValueError("Mismatch in input counts.")

            schedule, weights, urgency = create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours)
            weekly_chart = generate_weekly_chart(schedule, subjects, test_dates)
            weight_chart = generate_weight_chart(subjects, weights, urgency)
            progress_chart = generate_progress_chart(schedule)

            schedule_rows = "".join(
                [f"<tr><td>{s}</td><td>{h} hrs</td></tr>" for s, h in schedule.items()]
            )
            schedule_html = f"<table><tr><th>Subject</th><th>Allocated Hours</th></tr>{schedule_rows}</table>"

            closest_exam = min(test_dates, key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
            avg_hours = round(sum(schedule.values()) / len(subjects), 2)

            result = {
                "schedule": Markup(schedule_html),
                "weekly_chart": weekly_chart,
                "weight_chart": weight_chart,
                "progress_chart": progress_chart,
                "total_subjects": len(subjects),
                "total_hours": round(total_hours, 2),
                "closest_exam": closest_exam,
                "avg_hours": avg_hours
            }

        except Exception as e:
            error = f"⚠️ {str(e)}"

    return render_template_string(HTML_FORM, result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)
