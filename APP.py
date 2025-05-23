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

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Study Planner</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f4f4f4; }
        form, .result {
            background: white; padding: 20px; border-radius: 10px;
            max-width: 800px; margin-bottom: 30px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        input, textarea {
            width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box;
        }
        input[type="submit"] {
            background: #007BFF; color: white; border: none;
            cursor: pointer;
        }
        input[type="submit"]:hover { background: #0056b3; }
        h2 { color: #333; }
        .note { font-size: 0.9em; color: #666; }
        .schedule, .averages, .advice {
            background: #eef; padding: 10px; border-left: 5px solid #007BFF; margin-top: 15px;
        }
        .recommendation {
            background: #fffae6; padding: 10px; border-left: 5px solid #ffc107; margin-top: 15px;
        }
        img { max-width: 100%; height: auto; border-radius: 8px; }
        .daily-schedule-container {
            background: #eef; padding: 10px; border-left: 5px solid #28a745; margin-top: 15px;
        }
    </style>
</head>
<body>

<h1>📘 AI-Powered Study Planner</h1>

<form method="POST">
    <label>Subjects (comma-separated):</label>
    <input type="text" name="subjects" required>

    <label>Scores (comma-separated):</label>
    <input type="text" name="scores" required>

    <label>Desired Scores (comma-separated):</label>
    <input type="text" name="desired_scores" required>

    <label>Test Dates (YYYY-MM-DD, comma-separated):</label>
    <input type="text" name="dates" required>

    <label>Total Study Hours Available:</label>
    <input type="number" step="0.1" name="total_hours" required>

    <label>Past Study Hours (comma-separated):</label>
    <input type="text" name="study_hours" required>

    <label>Past Sleep Hours (comma-separated):</label>
    <input type="text" name="sleep_hours" required>

    <label>Score Fluctuations (comma-separated):</label>
    <input type="text" name="score_fluctuations" required>

    <label>Diet Quality (1-10):</label>
    <input type="number" name="diet_quality" min="1" max="10" required>

    <label>Exercise Frequency (1-10):</label>
    <input type="number" name="exercise_frequency" min="1" max="10" required>

    <input type="submit" value="Generate Study Plan">
</form>

{% if result %}
<div class="result">
    <h2>📊 Weekly Subject Study Distribution (Until Test Dates)</h2>
    <img src="data:image/png;base64,{{ result['weekly_chart'] }}" alt="Weekly Chart">

    <h2>📅 Allocated Total Study Hours</h2>
    <div class="schedule">{{ result['schedule'] }}</div>

    <h2>📈 Averages</h2>
    <div class="averages">
        Average Study Hours: {{ result['avg_study'] }} hrs/day<br>
        Average Sleep Hours: {{ result['avg_sleep'] }} hrs/night
    </div>

    <h2>🕒 Daily Study Schedule</h2>
    <div class="daily-schedule-container">
        <img src="data:image/png;base64,{{ result['daily_chart'] }}" alt="Daily Schedule">
    </div>

    <h2>⚠️ Burnout Detection</h2>
    <p><strong>Status:</strong> {{ result['burnout'] }}</p>
    {% if result['burnout'] == 'Burnout Detected' %}
    <div class="advice">
        💡 <strong>Advice:</strong><br>
        - Try reducing your study hours per day.<br>
        - Improve sleep duration (target 7–8 hours).<br>
        - Maintain consistent revision to reduce score fluctuations.<br>
        - Include relaxation techniques or physical activity daily.
    </div>
    {% endif %}

    {% if result['recommendations'] %}
    <h2>🍎 Health Recommendations</h2>
    <div class="recommendation">
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

def create_study_schedule(subjects, scores, desired_scores, test_dates, total_hours):
    today = datetime.today()
    urgency = [(datetime.strptime(d, "%Y-%m-%d") - today).days for d in test_dates]
    urgency = [max(u, 1) for u in urgency]
    improvement_needed = [max(0, d - s) for s, d in zip(scores, desired_scores)]
    weights = [imp / urg for imp, urg in zip(improvement_needed, urgency)]
    total_weight = sum(weights) if sum(weights) > 0 else 1
    allocations = [(w / total_weight) * total_hours for w in weights]
    return {subj: round(hours) for subj, hours in zip(subjects, allocations)}

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
    width = 0.1
    x = np.arange(max_weeks)

    for i, (subj, weeks) in enumerate(zip(subjects, subject_weeks)):
        weekly_allocation = schedule[subj] / weeks
        bars = [weekly_allocation if w < weeks else 0 for w in range(max_weeks)]
        ax.bar(x + i * width, bars, width=width, label=subj)

    ax.set_ylabel("Study Hours")
    ax.set_title("Weekly Subject Study Allocation (Until Test Dates)")
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

def generate_daily_schedule_chart(total_hours):
    start_time = datetime.strptime("10:00", "%H:%M")
    end_time = datetime.strptime("22:00", "%H:%M")
    day_hours = (end_time - start_time).seconds / 3600
    days_needed = math.ceil(total_hours / day_hours)
    daily_hours = total_hours / days_needed

    schedule_data = []
    current_time = start_time
    remaining_hours = daily_hours

    while remaining_hours > 0 and current_time < end_time:
        study_duration = min(1.5, remaining_hours)
        study_end_time = current_time + timedelta(hours=study_duration)
        if study_end_time <= end_time:
            schedule_data.append(('Study', current_time.strftime('%H:%M'), study_end_time.strftime('%H:%M')))
            current_time = study_end_time
            remaining_hours -= study_duration

            if remaining_hours > 0 and current_time < end_time:
                break_duration = min(0.5, remaining_hours)
                break_end_time = current_time + timedelta(hours=break_duration)
                if break_end_time <= end_time:
                    schedule_data.append(('Break', current_time.strftime('%H:%M'), break_end_time.strftime('%H:%M')))
                    current_time = break_end_time
                    remaining_hours -= break_duration
                else:
                    break
        else:
            break

    fig, ax = plt.subplots(figsize=(10, 6))
    y_ticks = []
    y_positions = []
    bar_height = 0.8
    current_y = 0

    for activity, start, end in schedule_data:
        start_dt = datetime.strptime(start, '%H:%M')
        end_dt = datetime.strptime(end, '%H:%M')
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        start_minutes = (start_dt - start_time).total_seconds() / 60
        total_day_minutes = (end_time - start_time).total_seconds() / 60

        bar_width = (duration_minutes / total_day_minutes)
        left = (start_minutes / total_day_minutes)

        color = 'skyblue' if activity == 'Study' else 'lightcoral'
        ax.barh(current_y, bar_width, left=left, height=bar_height, color=color, label=activity if current_y == 0 else "")
        ax.text(left + bar_width / 2, current_y, f"{start}-{end}", ha='center', va='center', color='black')

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

def detect_burnout(sleep_hours):
    avg_sleep = round(np.mean(sleep_hours), 2)
    return ("Burnout Detected" if avg_sleep < 6 else "No Burnout"), avg_sleep

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
        burnout_status, avg_sleep = detect_burnout(sleep_hours)
        avg_study = round(np.mean(study_hours), 2)
        daily_chart = generate_daily_schedule_chart(total_hours)
        schedule_str = "\n".join([f"{k}: {v} hrs" for k, v in schedule.items()])

        recommendations = []
        if diet_quality < 5:
            recommendations.append("🍏 Consider improving your diet. A nutritious diet boosts brain function and helps sustain energy levels.")
        if exercise_frequency < 5:
            recommendations.append("🏃 Try increasing your physical activity. Even light exercise can improve mood and focus.")

        result = {
            "schedule": schedule_str,
            "weekly_chart": weekly_chart,
            "daily_chart": daily_chart,
            "burnout": burnout_status,
            "avg_study": avg_study,
            "avg_sleep": avg_sleep,
            "recommendations": recommendations
        }

    return render_template_string(HTML_FORM, result=result)

if __name__ == "__main__":
    app.run(debug=True)
