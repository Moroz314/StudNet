FROM python:3.12-slim
RUN pip install --no-cache-dir --upgrade pip

ENV PYTHONUNBUFFERED=1

WORKDIR /studnet

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Convert Windows line endings to Unix format if needed
RUN sed -i 's/\r$//' .env 2>/dev/null || true

CMD ["python", "-m", "src.app"]
