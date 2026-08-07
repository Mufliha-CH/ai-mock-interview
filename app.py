"""Streamlit interface for the AI Mock Interview platform using Groq."""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from interviewer import InterviewEngine, ResponseFeedback


# Dynamic Role-to-Topic Mapping
ROLE_TOPICS = {
    "Data Scientist": [
        "Python (Pandas / NumPy)",
        "SQL & Query Optimization",
        "Machine Learning & Model Evaluation",
        "Statistics & Probability",
    ],
    "ML Engineer": [
        "Python & Object-Oriented Design",
        "Deep Learning Architectures (CNN / LSTM)",
        "Model Deployment & Streamlit / APIs",
        "PyTorch & TensorFlow Fundamentals",
    ],
    "Backend Developer": [
        "Python Data Structures & Algorithms",
        "SQL & Database Design",
        "System Design & Microservices",
        "RESTful APIs & Authentication",
    ],
    "Data Analyst": [
        "SQL & Aggregations",
        "Data Visualization & Dashboards",
        "Python for Data Wrangling",
        "Business Intelligence Concepts",
    ],
    "Full Stack Developer": [
        "Python Web Frameworks (FastAPI / Flask / Django)",
        "SQL & NoSQL Databases",
        "Frontend Integration & APIs",
        "Git & Version Control",
    ],
}

DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]


def get_api_key() -> str | None:
    """Retrieve Groq API key from local environment or Streamlit Secrets."""
    load_dotenv()
    # Check local .env first
    api_key = os.getenv("GROQ_API_KEY")

    # Fall back to Streamlit Cloud Secrets if deployed
    if not api_key and "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]

    return api_key


def get_engine() -> InterviewEngine | None:
    """Return an engine instance if an API key is present."""
    api_key = get_api_key()
    if not api_key:
        st.error(
            "⚠️ `GROQ_API_KEY` not found. Please add it to your `.env` file locally "
            "or to Streamlit Cloud Secrets when deployed."
        )
        return None
    return InterviewEngine(api_key=api_key)


def initialize_session_state() -> None:
    """Create persistent interview state for the current browser session."""
    defaults = {
        "chat_history": [],
        "current_question": None,
        "feedback_metrics": [],
        "topic_history": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_interview() -> None:
    """Clear all interview-specific state while keeping sidebar selections."""
    st.session_state.chat_history = []
    st.session_state.current_question = None
    st.session_state.feedback_metrics = []
    st.session_state.topic_history = []


def request_question(engine: InterviewEngine, role: str, topic: str, difficulty: str) -> None:
    """Generate and store the next question in the current session."""
    with st.spinner("Preparing your next question..."):
        question = engine.generate_question(
            role=role,
            topic=topic,
            difficulty=difficulty,
            topic_history=st.session_state.topic_history,
        )

    st.session_state.current_question = question
    st.session_state.topic_history.append(topic)
    st.session_state.chat_history.append({"role": "assistant", "content": question})


def display_feedback(feedback: ResponseFeedback) -> None:
    """Render structured evaluator feedback for one answer."""
    st.markdown(f"**Score:** `{feedback.score}/10`")
    st.markdown(f"**Technical Accuracy:** {feedback.technical_accuracy}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Key Strengths:**")
        for point in feedback.key_strengths:
            st.markdown(f"- {point}")
    with col2:
        st.markdown("**Areas for Improvement / Missing Points:**")
        for point in feedback.missing_points:
            st.markdown(f"- {point}")


# Page Setup
st.set_page_config(page_title="AI Mock Interview Platform", page_icon="🎯", layout="wide")
initialize_session_state()

st.title("🎯 AI Mock Interview Platform")
st.caption("Practice technical interviews with real-time AI-generated questions and structured evaluation.")

# Sidebar Configuration
with st.sidebar:
    st.header("Interview Setup")
    
    role = st.selectbox("Target Role", list(ROLE_TOPICS.keys()))
    # Dynamically change available topics based on selected role
    topic = st.selectbox("Primary Topic", ROLE_TOPICS[role])
    difficulty = st.select_slider("Difficulty Level", options=DIFFICULTIES, value="Intermediate")

    st.markdown("---")
    new_interview = st.button("Start New Interview Session", type="primary", use_container_width=True)

if new_interview:
    reset_interview()
    engine = get_engine()
    if engine:
        try:
            request_question(engine, role, topic, difficulty)
            st.rerun()
        except Exception as error:
            st.error(f"Could not generate a question: {error}")

# Performance Metrics Summary
if st.session_state.feedback_metrics:
    scores = [item["score"] for item in st.session_state.feedback_metrics]
    avg_score = sum(scores) / len(scores)

    m1, m2 = st.columns(2)
    m1.metric("Questions Evaluated", len(scores))
    m2.metric("Average Score", f"{avg_score:.1f} / 10")

    with st.expander("Session Performance Summary"):
        st.dataframe(pd.DataFrame(st.session_state.feedback_metrics), use_container_width=True)

# Interactive Conversation View
if st.session_state.current_question is None:
    st.info("👈 Choose your role and topic in the sidebar, then select **Start New Interview Session** to begin.")
else:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("feedback"):
                display_feedback(ResponseFeedback.model_validate(message["feedback"]))

    candidate_answer = st.chat_input("Write your response or pseudocode here...")
    if candidate_answer:
        question = st.session_state.current_question
        st.session_state.chat_history.append({"role": "user", "content": candidate_answer})

        engine = get_engine()
        if engine:
            try:
                with st.spinner("Evaluating your response..."):
                    feedback = engine.evaluate_response(question, candidate_answer)

                feedback_data = feedback.model_dump()
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": "### 📊 Answer Feedback",
                        "feedback": feedback_data,
                    }
                )
                st.session_state.feedback_metrics.append(
                    {
                        "question_number": len(st.session_state.feedback_metrics) + 1,
                        "role": role,
                        "topic": topic,
                        "difficulty": difficulty,
                        "score": feedback.score,
                    }
                )
                request_question(engine, role, topic, difficulty)
                st.rerun()
            except Exception as error:
                st.error(f"Could not evaluate the answer: {error}")