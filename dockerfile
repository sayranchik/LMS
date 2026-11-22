FROM python:3.13-slim

ENV DJANGO_SECRET_KEY=django-insecure-42o%s#g$j#y2v7d3h(2z+1u0r1375m95j+9qk5d8u+8b$#@)
ENV DJANGO_DEBUG=0
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