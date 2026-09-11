FROM python:3.11.15-slim AS build
RUN python -m venv --without-pip /opt/venv
COPY requirements.lock.txt /tmp/requirements.lock.txt
RUN python -m pip --python /opt/venv/bin/python install --no-cache-dir --no-deps \
    -r /tmp/requirements.lock.txt
RUN /opt/venv/bin/python -c "from network_as_code import NetworkAsCodeApi; import fastapi, segno"

FROM python:3.11.15-slim
RUN useradd -m -u 1000 user \
 && python -m pip uninstall -y pip setuptools
COPY --from=build /opt/venv /opt/venv
ENV HOME=/home/user PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /home/user/app
COPY --chown=user app ./app
COPY --chown=user demo ./demo
COPY --chown=user migrations ./migrations
COPY --chown=user alembic.ini pyproject.toml start.py ./
USER user
ENV ISNAD_LLM_MAX_CALLS_PER_HOUR=120 \
    ISNAD_RATE_LIMIT_PER_IP=40 \
    ISNAD_DEMO_MODE=true \
    ISNAD_PROVIDER=mock \
    ISNAD_PLANNER=llm \
    ISNAD_MERCHANT_API_KEYS=demo-merchant-key \
    ISNAD_VAULT_TRUSTED_PUBLIC_KEYS=4034e169495122a893d8fe6738c2b0f54655fdfb6ec3c6d0eeb938d1330e7f9f \
    ISNAD_DATABASE_URL=sqlite:////home/user/data/isnad-demo.db \
    ISNAD_VAULT_KEY_PATH=/home/user/data/vault-key.pem
RUN mkdir -p /home/user/data
EXPOSE 7860
CMD ["python", "start.py"]
