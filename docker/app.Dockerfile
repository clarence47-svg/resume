ARG SERVICE_IMAGE=profile-agent-service:local
FROM ${SERVICE_IMAGE}

CMD [".venv/bin/streamlit", "run", "src/streamlit_app.py", "--server.address=0.0.0.0"]
