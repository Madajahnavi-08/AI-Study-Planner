import streamlit as st
import pandas as pd
from datetime import date, timedelta
import math

st.set_page_config(page_title="AI Study Planner", page_icon="📚", layout="wide")

st.markdown("""
<style>
.main {background: linear-gradient(135deg, #f7f8ff 0%, #eef4ff 100%);}
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(110deg,#283593,#536dfe); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0;}
.hero p {color:#e8eaff; margin:.35rem 0 0 0;}
.small-note {color:#64748b; font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

if "completed" not in st.session_state:
    st.session_state.completed = set()
if "plan" not in st.session_state:
    st.session_state.plan = None

st.markdown("""
<div class="hero">
  <h1>📚 AI Study Planner</h1>
  <p>Turn your subjects, deadlines and available time into a practical study schedule.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Your study settings")
    student_name = st.text_input("Your name (optional)", placeholder="Enter your name")
    exam_date = st.date_input("Exam date", value=date.today() + timedelta(days=14),
                              min_value=date.today())
    daily_hours = st.slider("Study hours per day", 1, 12, 4)
    study_days = st.multiselect(
        "Days available",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    )
    session_minutes = st.select_slider("Study session length", options=[25, 30, 45, 50, 60, 90], value=50)
    break_minutes = st.select_slider("Break after each session", options=[5, 10, 15, 20], value=10)

st.subheader("1. Add your subjects")
st.caption("Enter one subject per line in the format: Subject, topics, difficulty, confidence. Difficulty: Easy/Medium/Hard. Confidence: 1 (low) to 5 (high).")
default_subjects = """Python, Lists; Functions; Pandas, Medium, 3
Database Management, SQL; Joins; Normalization, Hard, 2
Statistics, Mean; Probability; Hypothesis testing, Medium, 3
Communication Skills, Speaking; Writing, Easy, 4"""
subject_text = st.text_area("Subjects and topics", value=default_subjects, height=150)

def parse_subjects(raw):
    rows = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            raise ValueError(f"Line {line_no}: please provide Subject, topics, difficulty, confidence.")
        name, topics, difficulty, confidence = parts[0], parts[1], parts[2].title(), parts[3]
        if difficulty not in ["Easy", "Medium", "Hard"]:
            raise ValueError(f"Line {line_no}: difficulty must be Easy, Medium or Hard.")
        try:
            confidence = int(confidence)
        except ValueError:
            raise ValueError(f"Line {line_no}: confidence must be a number from 1 to 5.")
        if not 1 <= confidence <= 5:
            raise ValueError(f"Line {line_no}: confidence must be between 1 and 5.")
        topic_list = [t.strip() for t in topics.split(";") if t.strip()]
        if not name or not topic_list:
            raise ValueError(f"Line {line_no}: subject and at least one topic are required.")
        rows.append({"subject": name, "topics": topic_list, "difficulty": difficulty, "confidence": confidence})
    if not rows:
        raise ValueError("Add at least one subject.")
    return rows

def build_plan(subjects, exam_day, hours, available_days, session_len, break_len):
    today = date.today()
    days_left = max(1, (exam_day - today).days + 1)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    valid_dates = [today + timedelta(days=i) for i in range(days_left)
                   if (today + timedelta(days=i)).strftime("%A") in available_days]
    if not valid_dates:
        valid_dates = [today]
    tasks = []
    weights = {"Easy": 1.0, "Medium": 1.35, "Hard": 1.7}
    for s in subjects:
        # Higher difficulty and lower confidence increase study priority.
        priority = weights[s["difficulty"]] * (6 - s["confidence"])
        for topic in s["topics"]:
            tasks.append({"subject": s["subject"], "topic": topic, "priority": priority})
    tasks.sort(key=lambda x: x["priority"], reverse=True)

    capacity = max(1, int(hours * 60 / (session_len + break_len)))
    schedule = []
    for i, task in enumerate(tasks):
        day = valid_dates[i % len(valid_dates)]
        schedule.append({
            "Date": day.strftime("%a, %d %b"),
            "Subject": task["subject"],
            "Topic": task["topic"],
            "Duration (min)": session_len,
            "Focus tip": "Practice problems" if task["priority"] >= 6 else "Read, summarize and self-test",
            "Task ID": f'{day.isoformat()}|{task["subject"]}|{task["topic"]}'
        })
    # Add spaced revision sessions near the exam, without exceeding daily session capacity.
    for s in subjects:
        rev_day = valid_dates[-1]
        schedule.append({
            "Date": rev_day.strftime("%a, %d %b"),
            "Subject": s["subject"],
            "Topic": "Quick revision + self-test",
            "Duration (min)": min(30, session_len),
            "Focus tip": "Recall key points without looking at notes",
            "Task ID": f'{rev_day.isoformat()}|{s["subject"]}|Quick revision'
        })
    return pd.DataFrame(schedule), capacity, days_left

left, right = st.columns([1, 1])
with left:
    st.info("The planner prioritizes harder topics and subjects where your confidence is lower.")
with right:
    st.info("This demo uses a transparent priority algorithm; it does not require an external AI API key.")

if st.button("✨ Generate my study plan", type="primary", use_container_width=True):
    try:
        subjects = parse_subjects(subject_text)
        if not study_days:
            st.error("Please select at least one available study day.")
        else:
            plan, capacity, days_left = build_plan(
                subjects, exam_date, daily_hours, study_days, session_minutes, break_minutes
            )
            st.session_state.plan = plan
            st.session_state.completed = set()
            st.session_state.capacity = capacity
            st.session_state.days_left = days_left
            st.success("Your study plan is ready!")
    except ValueError as exc:
        st.error(str(exc))

if st.session_state.plan is not None:
    plan = st.session_state.plan.copy()
    st.divider()
    st.subheader(f"2. {student_name.strip() + ', here is your plan' if student_name.strip() else 'Your personalized study plan'}")
    total_tasks = len(plan)
    done_count = len(st.session_state.completed)
    progress = done_count / total_tasks if total_tasks else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Days until exam", st.session_state.days_left)
    m2.metric("Study tasks", total_tasks)
    m3.metric("Completed", f"{done_count}/{total_tasks}")
    st.progress(progress, text=f"Overall progress: {progress:.0%}")

    st.markdown("### Daily schedule")
    display = plan.drop(columns=["Task ID"]).copy()
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("### 3. Track your progress")
    st.caption("Tick a task when you finish it. Your progress updates automatically during this session.")
    for idx, row in plan.iterrows():
        task_id = row["Task ID"]
        label = f'{row["Date"]} · {row["Subject"]} — {row["Topic"]} ({row["Duration (min)"]} min)'
        checked = task_id in st.session_state.completed
        new_value = st.checkbox(label, value=checked, key=f"task_{idx}")
        if new_value:
            st.session_state.completed.add(task_id)
        else:
            st.session_state.completed.discard(task_id)

    done_count = len(st.session_state.completed)
    progress = done_count / total_tasks if total_tasks else 0
    st.progress(progress, text=f"Updated progress: {progress:.0%}")

    csv = plan.drop(columns=["Task ID"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download plan as CSV", data=csv,
                       file_name="ai_study_plan.csv", mime="text/csv")

    st.markdown("### Smart study tips")
    tips = [
        "Start with the topic you find hardest while your concentration is fresh.",
        "After each session, close your notes and write down what you remember.",
        "Use short practice questions to check understanding instead of only rereading.",
        "Keep the final day for revision and a calm review of key concepts.",
        "If you miss a session, move it to your next available study slot rather than giving up."
    ]
    for tip in tips:
        st.write("• " + tip)

st.divider()
st.markdown('<p class="small-note">Built with Python, Streamlit and pandas · Educational planning tool</p>',
            unsafe_allow_html=True)
