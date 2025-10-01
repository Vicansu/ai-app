from flask import Flask, request, render_template_string
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import math

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
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #c9e6ff, #f9f0ff);
            color: #333;
        }
        h1 {
            text-align: center;
            color: #0056b3;
            padding: 30px;
            background: rgba(255,255,255,0.8);
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        form, .result {
            background: white;
            padding: 25px;
            border-radius: 15px;
            max-width: 900px;
            margin: 30px auto;
            margin-bottom: 40px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        label {
            font-weight: bold;
            margin-top: 10px;
            display: block;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-sizing: border-box;
            font-size: 0.95em;
        }
        input[type="submit"] {
            background: linear-gradient(90deg, #007BFF, #00c6ff);
            color: white;
            border: none;
            font-size: 1.1em;
            border-radius: 8px;
            padding: 14px;
            cursor: pointer;
            margin-top: 15px;
            transition: background 0.3s ease;
        }
        input[type="submit"]:hover {
            background: linear-gradient(90deg, #0056b3, #0095cc);
        }
        h2 {
            margin-top: 30px;
            color: #222;
        }
        .section {
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        .schedule { background: #eef7ff; border-left: 5px solid #007BFF; }
        .averages { background: #f0f7f0; border-left: 5px solid #28a745; }
        .advice { background: #fff4f4; border-left: 5px solid #dc3545; }
        .recommendation { background: #fff8e6; border-left: 5px solid #ffc107; }
        .chart-container { text-align: center; margin-top: 20px; }
        img { max-width: 100%; height: auto; border-radius: 10px; margin-top: 10px; }
        .highlight { font-weight: bold; color: #d63384; }
    </style>
</head>
<body>

<h1>📘 AI-Powered Study Planner 🚀</h1>

<form method="POST">
    <label>📚 Subjects (comma-separated):</label>
    <input type="text" name="subjects" placeholder="e.g. Math, Physics, History" required>

    <label>📝 Current Scores (comma-separated):</label>
    <input type="text" name="scores" placeholder="e.g. 70, 80, 65" required>

    <label>🎯 Desired Scores (comma-separated):</label>
    <input type="text" name="desired_scores" placeholder="e.g. 90, 85, 80" required>

    <label>📅 Test Dates (YYYY-MM-DD, comma-separated):</label>
    <input type="text" name="dates" placeholder="e.g. 2025-11-10, 2025-12-05" required>

    <label>⏳ Total Study Hours Available:</label>
    <input type="number" step="0.1" name="total_hours" placeholder="e.g. 120" required>

    <label>📖 Past Study Hours (comma-separated):</label>
    <input type="text" name="study_hours" placeholder="e.g. 3, 4, 5, 2, 6" required>

    <label>💤 Past Sleep Hours (comma-separated):</label>
    <input type="text" name="sleep_hours" placeholder="e.g. 7, 6, 5, 8, 6" required>

    <label>📉 Score Fluctuations (comma-separated):</label>
    <input type="text" name="score_fluctuations" placeholder="e.g. 2, 5, 8, 3" required>

    <label>🥗 Diet Quality (1-10):</label>
    <input type="number" name="diet_quality" min="1" max="10" placeholder="10 = Excellent, 1 = Poor" required>

    <label>🏃 Exercise Frequency (1-10):</label>
    <input type="number" name="exercise_frequency" min="1" max="10" placeholder="10 = Daily, 1 = Rarely" required>

    <input type="submit" value="✨ Generate My Smart Study Plan ✨">
</form>

{% if result %}
<div class="result">
    <h2>📊 Weekly Subject Study Distribution</h2>
    <div class="chart-container">
        <img src="data:image/png;base64,{{ result['weekly_chart'] }}" alt="Weekly Chart">
    </div>

    <h2>📅 Allocated Total Study Hours</h2>
    <div class="section schedule">{{ result['schedule'] }}</div>

    <h2>📈 Averages</h2>
    <div class="section averages">
        Average Study Hours: <span class="highlight">{{ result['avg_study'] }}</span> hrs/day<br>
        Average Sleep Hours: <span class="highlight">{{ result['avg_sleep'] }}</span> hrs/night
    </div>

    <h2>🕒 Daily Study Schedule</h2>
    <div class="chart-container">
        <img src="data:image/png;base64,{{ result['daily_chart'] }}" alt="Daily Schedule">
    </div>

    <h2>⚠️ Burnout Detection</h2>
    <p><strong>Status:</strong> {{ result['burnout'] }}</p>
    {% if result['burnout'] == 'Burnout Detected' %}
    <div class="section advice">
        💡 <strong>Personalized Advice:</strong><br>
        {% for tip in result['burnout_tips'] %}
            - {{ tip }}<br>
        {% endfor %}
    </div>
    {% endif %}

    {% if result['recommendations'] %}
    <h2>🍎 Health & Lifestyle Recommendations</h2>
    <div class="section recommendation">
        {% for rec in result['recommendations'] %}
            <p>{{ rec }}</p>
        {% endfor %}
    </div>
    {% endif %}
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
    weights = [imp / urg for imp, urg in zip(improvement_needed, urgency)]
    total_weight = sum(weights) if sum(weights) > 0 else 1
    allocations = [(w / total_weight) * total_hours for w in weights]
    return {subj: round(hours, 1) for subj, hours in zip(subjects, allocations)}

def generate_weekly_chart(schedule, subjects, test_dates):
    today = datetime.today()
    subject_weeks = []
    max_weeks = 0

    for date_str in test_dates:
        test_date = datetime.strptime(date_str, "%Y-%m-%d")
        weeks_until = max(1, (test_date - today).days // 7)
        subject_weeks.append(weeks_until)
        max_weeks = max(max_weeks, weeks_until)

    fig, ax = plt.subplots(figsize=(10, 6))
    width = 0.8 / len(subjects)
    x = np.arange(max_weeks)
    colors = plt.cm.tab10(np.linspace(0, 1, len(subjects)))

    for i, (subj, weeks) in enumerate(zip(subjects, subject_weeks)):
        weekly_allocation = schedule[subj] / weeks
        bars = [weekly_allocation if w < weeks else 0 for w in range(max_weeks)]
        ax.bar(x + i * width, bars, width=width, label=subj, color=colors[i])

    ax.set_ylabel("Study Hours")
    ax.set_title("Weekly Subject Study Allocation")
    ax.set_xlabel("Weeks from Now")
    ax.set_xticks(x + width * len(subjects) / 2)
    ax.set_xticklabels([f"Week {i+1}" for i in range(max_weeks)])
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return chart_base64

def generate_daily_schedule_chart(schedule, total_hours):
    start_time = datetime.strptime("10:00", "%H:%M")
    end_time = datetime.strptime("22:00", "%H:%M")
    day_hours = (end_time - start_time).seconds / 3600
    days_needed = math.ceil(total_hours / day_hours)
    daily_hours = total_hours / days_needed

    subjects = list(schedule.keys())
    study_plan = []
    current_time = start_time
    remaining_hours = daily_hours

    subject_index = 0
    while remaining_hours > 0 and current_time < end_time:
        subj = subjects[subject_index % len(subjects)]
        study_duration = min(1.5, remaining_hours)
        study_end_time = current_time + timedelta(hours=study_duration)
        if study_end_time <= end_time:
            study_plan.append((subj, current_time.strftime('%H:%M'), study_end_time.strftime('%H:%M')))
            current_time = study_end_time
            remaining_hours -= study_duration

            if remaining_hours > 0:
                break_duration = 0.5
                break_end_time = current_time + timedelta(hours=break_duration)
                if break_end_time <= end_time:
                    study_plan.append(("Break", current_time.strftime('%H:%M'), break_end_time.strftime('%H:%M')))
                    current_time = break_end_time
            subject_index += 1
        else:
            break

    fig, ax = plt.subplots(figsize=(10, 6))
    y_ticks = []
    y_positions = []
    bar_height = 0.8
    current_y = 0

    colors = plt.cm.tab10(np.linspace(0, 1, len(subjects)))

    for activity, start, end in study_plan:
        start_dt = datetime.strptime(start, '%H:%M')
        end_dt = datetime.strptime(end, '%H:%M')
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        start_minutes = (start_dt - start_time).total_seconds() / 60
        total_day_minutes = (end_time - start_time).total_seconds() / 60

        bar_width = (duration_minutes / total_day_minutes)
        left = (start_minutes / total_day_minutes)

        if activity == "Break":
            color = 'lightcoral'
        else:
            idx = subjects.index(activity)
            color = colors[idx]

        ax.barh(current_y, bar_width, left=left, height=bar_height, color=color, label=activity if activity != "Break" else "")
        ax.text(left + bar_width / 2, current_y, f"{activity} ({start}-{end})", ha='center', va='center', color='black', fontsize=8)

        y_positions.append(current_y)
        y_ticks.append("")
        current_y += 1

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_ticks)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Time of Day")
    ax.set_title("Daily Study Schedule")
    ax.set_xticks(np.linspace(0, 1, 13))
    ax.set_xticklabels([(start_time + timedelta(hours=i)).strftime('%I:%M %p') for i in range(0, 13)], rotation=45, ha='right')
    ax.invert_yaxis()
    ax.legend(loc='upper right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return chart_base64

def detect_burnout(study_hours, sleep_hours, score_fluctuations):
    avg_sleep = round(np.mean(sleep_hours), 2)
    avg_study = round(np.mean(study_hours), 2)
    fluct = round(np.std(score_fluctuations), 2)

    burnout_tips = []
    burnout_status = "No Burnout"
    if avg_sleep < 6 or avg_study > 10 or fluct > 15:
        burnout_status = "Burnout Detected"
        if avg_sleep < 6:
            burnout_tips.append("😴 Try to increase sleep to at least 7–8 hours.")
        if avg_study > 10:
            burnout_tips.append("📉 Studying more than 10 hours/day is counterproductive.")
        if fluct > 15:
            burnout_tips.append("🔄 Reduce score fluctuations by revising consistently instead of cramming.")

    return burnout_status, avg_sleep, avg_study, burnout_tips

# =========================
# MAIN ROUTE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        subjects = [s.strip() for s in request.form["subjects"].split(",")]
        scores = list(map(int, request.form["scores"].split(",")))
        desired_scores = list(map(int, request.form["desired_scores"].split(",")))
        test_dates = [s.strip() for s in request.form["dates"].split(",")]
        total_hours = float(request.form["total_hours"])
        study_hours = list(map(float, request.form["study_hours"].split(",")))
        sleep_hours = list(map(float, request.form["sleep_hours"].split(",")))
        score_fluctuations = list(map(float, request.form["score_fluctuations"].split(",")))
        diet_quality = int(request.form["diet_quality"])
        exercise_frequency = int(request.form["exercise_frequency"])

        schedule = create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours)
        weekly_chart = generate_weekly_chart(schedule, subjects, test_dates)
        daily_chart = generate_daily_schedule_chart(schedule, total_hours)

        burnout_status, avg_sleep, avg_study, burnout_tips = detect_burnout(study_hours, sleep_hours, score_fluctuations)

        schedule_str = "<br>".join([f"<b>{k}</b>: {v} hrs" for k, v in schedule.items()])

        recommendations = []
        if diet_quality < 5:
            recommendations.append("🥦 Improve diet quality with balanced meals (fruits, veggies, whole grains).")
        if exercise_frequency < 5:
            recommendations.append("🏃 Try exercising at least 3 times per week to boost energy.")
        if avg_sleep < 7:
            recommendations.append("💤 Aim for 7–8 hours of sleep each night for peak focus.")
        if avg_study > 9:
            recommendations.append("⚖️ Balance study with breaks — efficiency > long hours!")

        result = {
            "schedule": schedule_str,
            "weekly_chart": weekly_chart,
            "daily_chart": daily_chart,
            "burnout": burnout_status,
            "avg_study": avg_study,
            "avg_sleep": avg_sleep,
            "recommendations": recommendations,
            "burnout_tips": burnout_tips
        }

    return render_template_string(HTML_FORM, result=result)

if __name__ == "__main__":
    app.run(debug=True)
