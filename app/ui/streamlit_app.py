"""Streamlit onboarding entry point for Module 2."""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st

from app.config import get_settings
from app.database.init_db import initialize_database
from app.database.session import SessionLocal
from app.logging_config import configure_logging
from app.schemas.assessment import SkillAssessmentInput
from app.services.assessment_service import DATA_ENGINEERING_SKILLS, DIAGNOSTIC_QUESTIONS, assess_skills
from app.services.onboarding_service import SKILL_LEVELS, get_existing_onboarding_profile, save_onboarding_profile
from app.services.progress_service import get_progress_dashboard

settings = get_settings()
configure_logging(settings.log_level)
initialize_database()
st.set_page_config(page_title=settings.app_name, page_icon="🎓")
st.title("Data Engineering Learning Coach")
st.caption("Learner onboarding")


@contextmanager
def database_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _choice(label: str, value: str | None) -> str:
    return st.selectbox(label, SKILL_LEVELS, index=SKILL_LEVELS.index(value) if value in SKILL_LEVELS else 0)


def _value(profile: object | None, field: str) -> str:
    return str(getattr(profile, field, "") or "")


def profile_form(profile: object | None) -> None:
    with st.form("onboarding_profile"):
        st.subheader("About you")
        current_role = st.text_input("Current role *", value=_value(profile, "current_role"))
        experience_years = st.number_input("Years of experience *", 0.0, 80.0, value=float(getattr(profile, "experience_years", 0.0)), step=0.5)
        education = st.text_input("Education *", value=_value(profile, "education"))
        st.subheader("Current skills")
        labels = {"python_level": "Python level *", "sql_level": "SQL level *", "database_experience": "Database experience *", "cloud_experience": "Cloud experience *", "git_github_level": "Git/GitHub level *", "linux_level": "Linux level *", "etl_elt_level": "ETL/ELT level *", "data_warehousing_level": "Data warehousing level *", "spark_pyspark_level": "Spark/PySpark level *", "airflow_orchestration_level": "Airflow/orchestration level *", "docker_level": "Docker level *"}
        skills = {field: _choice(label, getattr(profile, field, None)) for field, label in labels.items()}
        projects = st.text_area("Existing projects (optional)", value=_value(profile, "existing_projects"), help="Leave blank if you have none.")
        st.subheader("Your goal")
        target_role = st.text_input("Target role *", value=_value(profile, "target_role"))
        company_type = st.text_input("Target company type *", value=_value(profile, "target_company_type"))
        cloud_options = ("AWS", "Azure", "GCP", "No preference")
        cloud = getattr(profile, "preferred_cloud", "AWS") or "AWS"
        preferred_cloud = st.selectbox("Preferred cloud *", cloud_options, index=cloud_options.index(cloud) if cloud in cloud_options else 0)
        hours = st.number_input("Study hours per week *", 1.0, 168.0, value=float(getattr(profile, "study_hours_per_week", 5.0) or 5.0), step=1.0)
        timeline = st.text_input("Target timeline *", value=_value(profile, "target_timeline"))
        preferences = ("Hands-on projects", "Structured lessons", "Mixed", "Reading and videos")
        preference = getattr(profile, "learning_preference", preferences[0]) or preferences[0]
        learning_preference = st.selectbox("Learning preference *", preferences, index=preferences.index(preference) if preference in preferences else 0)
        submitted = st.form_submit_button("Save profile")
    if submitted:
        payload = {"current_role": current_role, "experience_years": experience_years, "education": education, **skills, "existing_projects": projects, "target_role": target_role, "target_company_type": company_type, "preferred_cloud": preferred_cloud, "study_hours_per_week": hours, "target_timeline": timeline, "learning_preference": learning_preference}
        try:
            with database_session() as session:
                save_onboarding_profile(session, payload)
            st.session_state.profile_saved = True
            st.session_state.edit_profile = False
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _optional_score(label: str, key: str) -> float | None:
    """Collect an optional 0--10 score while preserving a valid score of zero."""
    included = st.checkbox(f"Add {label}", key=f"include_{key}")
    if not included:
        return None
    return st.number_input(label, min_value=0.0, max_value=10.0, value=0.0, step=0.5, key=key)


def assessment_form() -> None:
    """Render Module 3 evidence entry and the requested results table."""
    st.subheader("Data engineering skill assessment")
    st.caption("Use 1–10 scores. Optional evidence makes the result more reliable than self-report alone.")
    with st.form("skill_assessment"):
        inputs: list[SkillAssessmentInput] = []
        for skill in DATA_ENGINEERING_SKILLS:
            with st.expander(skill):
                self_report = st.slider(f"{skill} — self-reported score", 1, 10, 3, key=f"self_{skill}")
                target = st.slider(f"{skill} — target score", self_report, 10, max(self_report, 7), key=f"target_{skill}")
                question, choices, correct_answer = DIAGNOSTIC_QUESTIONS[skill]
                include_diagnostic = st.checkbox("Answer optional diagnostic question", key=f"include_diagnostic_{skill}")
                diagnostic = None
                if include_diagnostic:
                    answer = st.radio(question, choices, key=f"diagnostic_{skill}")
                    diagnostic = 10.0 if answer == correct_answer else 0.0
                quiz = _optional_score(f"{skill} — quiz score (optional)", f"quiz_{skill}")
                project = _optional_score(f"{skill} — project evidence score (optional)", f"project_{skill}")
                inputs.append(SkillAssessmentInput(skill=skill, self_reported_score=self_report, target_score=target,
                                                   diagnostic_score=diagnostic, quiz_score=quiz,
                                                   project_evidence_score=project))
        submitted = st.form_submit_button("Calculate assessment")
    if submitted:
        try:
            st.session_state.assessment_results = assess_skills(inputs)
        except ValueError as error:
            st.error(str(error))
    results = st.session_state.get("assessment_results")
    if results:
        st.table([{"Skill": item.skill, "Score": item.current_score, "Level": item.level,
                   "Gap": item.gap, "Priority": item.priority} for item in results])
        st.caption("Confidence reflects evidence supplied. Self-report-only results are low confidence.")


def progress_dashboard(learner_id: int) -> None:
    """Render Module 9 progress tracking from durable learner state."""
    with database_session() as session:
        dashboard = get_progress_dashboard(
            session,
            learner_id,
            roadmap=st.session_state.get("personalized_roadmap"),
        )

    st.subheader("Learner Progress Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Progress", f"{dashboard.overall_progress_percentage}%")
    col2.metric("Roadmap Completion", f"{dashboard.roadmap_completion_percentage}%")
    col3.metric("Study Streak", f"{dashboard.study_streak_days} days")
    quiz_value = "No attempts" if dashboard.quiz_average_score is None else f"{dashboard.quiz_average_score}/10"
    col4.metric("Quiz Average", quiz_value)

    st.markdown("### Current Phase")
    if dashboard.current_phase is None:
        st.info("No roadmap phases are available yet.")
    else:
        st.write(f"Phase {dashboard.current_phase.phase}: {dashboard.current_phase.goal}")
        st.progress(dashboard.current_phase.completion_percentage / 100)
        st.caption(
            f"{dashboard.current_phase.completed_topics}/{dashboard.current_phase.total_topics} topics completed"
        )

    st.markdown("### What should I do next?")
    st.info(f"{dashboard.next_recommendation.title} — {dashboard.next_recommendation.rationale}")

    skills_tab, topics_tab, tasks_tab, weak_tab, projects_tab, quizzes_tab = st.tabs(
        ["Skills", "Completed Topics", "Upcoming Tasks", "Weak Areas", "Project Progress", "Recent Quiz Performance"]
    )
    with skills_tab:
        if dashboard.skills:
            st.table(
                [
                    {
                        "Skill": skill.skill,
                        "Current": skill.current_score,
                        "Target": skill.target_score,
                        "Progress": f"{skill.progress_to_target_percentage}%",
                        "Gap": skill.improvement_needed,
                    }
                    for skill in dashboard.skills
                ]
            )
        else:
            st.info("No skill records are tracked yet.")
    with topics_tab:
        if dashboard.completed_topics:
            st.table(
                [
                    {
                        "Topic": topic.topic,
                        "Score": topic.score,
                        "Completed": f"{topic.completion_percentage}%",
                    }
                    for topic in dashboard.completed_topics
                ]
            )
        else:
            st.info("No completed topics yet.")
    with tasks_tab:
        if dashboard.upcoming_tasks:
            st.table(
                [
                    {
                        "Topic": topic.topic,
                        "Status": topic.status,
                        "Progress": f"{topic.completion_percentage}%",
                    }
                    for topic in dashboard.upcoming_tasks
                ]
            )
        else:
            st.info("No upcoming tracked tasks.")
    with weak_tab:
        if dashboard.weak_areas:
            st.table(
                [
                    {
                        "Skill": skill.skill,
                        "Current": skill.current_score,
                        "Target": skill.target_score,
                        "Gap": skill.improvement_needed,
                    }
                    for skill in dashboard.weak_areas
                ]
            )
        else:
            st.success("No weak areas are currently tracked.")
    with projects_tab:
        if dashboard.projects:
            st.table(
                [
                    {
                        "Project": project.project_name,
                        "Status": project.status,
                        "Progress": f"{project.completion_percentage}%",
                        "Technologies": ", ".join(project.technologies),
                    }
                    for project in dashboard.projects
                ]
            )
        else:
            st.info("No projects are tracked yet.")
    with quizzes_tab:
        if dashboard.recent_quiz_performance:
            st.table(
                [
                    {
                        "Topic": quiz.topic,
                        "Difficulty": quiz.difficulty,
                        "Score": quiz.score,
                        "Recommended Action": quiz.recommended_action,
                    }
                    for quiz in dashboard.recent_quiz_performance
                ]
            )
        else:
            st.info("No quiz attempts yet.")


with database_session() as session:
    profile = get_existing_onboarding_profile(session)

if profile is not None and not st.session_state.get("edit_profile", False):
    if st.session_state.pop("profile_saved", False):
        st.success("Profile created successfully.")
    st.success("Your onboarding profile is ready.")
    st.write(f"Current role: {profile.current_role} · Target role: {profile.target_role}")
    if st.button("Edit profile"):
        st.session_state.edit_profile = True
        st.rerun()
    progress_dashboard(profile.learner_id)
    assessment_form()
else:
    profile_form(profile)
