FROM python:3.12-slim
WORKDIR /work
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CODEX_MINI_WORKSPACE=/work/shop PYTHONUNBUFFERED=1
CMD ["pytest", "-v"]
