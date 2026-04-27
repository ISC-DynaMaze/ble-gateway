FROM --platform=arm64 dtcooper/raspberrypi-os:python3.13

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app
RUN pip install .

COPY . /app

CMD ["python3", "main.py"]