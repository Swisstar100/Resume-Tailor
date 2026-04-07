FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fontconfig \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

COPY wkhtmltox_0.12.6.1-3.bookworm_amd64.deb .
RUN apt-get update && dpkg -i wkhtmltox_0.12.6.1-3.bookworm_amd64.deb || apt-get install -fy \
    && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE  8004

CMD ["gunicorn", "restailor.wsgi:application"]