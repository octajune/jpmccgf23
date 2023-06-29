FROM python:3.6-slim-buster

COPY requirements.txt .

RUN pip install --default-timeout=10000000 -r requirements.txt

COPY . .

EXPOSE 443

CMD ["flask", "run", "--host=0.0.0.0", "--port=443"]
