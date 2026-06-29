FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-robot-lite.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-robot-lite.txt

COPY . .
RUN mkdir -p data/uploads data/robot_observations

ENV SIMULATOR_MODE=auto
ENV APP_MODE=production
ENV PORT=7860

EXPOSE 7860

CMD ["python", "app.py"]