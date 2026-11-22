FROM python:3.13-slim

ENV DJANGO_SECRET_KEY=django-insecure-0q6zg0g4=!yf6472&c62@3v&_3l@!0=i_2p2!5i9!4o39q4y
ENV DJANGO_DEBUG=1
ENV PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chown -R 1000:1000 /app
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
USER 1000

EXPOSE 8000
CMD ["gunicorn", "LMS.wsgi:application", "--bind", "0.0.0.0:8000"]