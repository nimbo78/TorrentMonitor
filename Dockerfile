FROM php:8.2-apache

RUN apt-get update && apt-get install -y \
        libcurl4-openssl-dev \
        libpq-dev \
        libsqlite3-dev \
        cron \
    && docker-php-ext-install curl pdo pdo_mysql pdo_pgsql pdo_sqlite \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

COPY . .

RUN cp config.php.example config.php \
    && chmod -R 755 /var/www/html \
    && chown -R www-data:www-data /var/www/html

# Cron для engine.php каждые 30 минут
RUN echo "*/30 * * * * www-data php /var/www/html/engine.php >> /var/log/tm-engine.log 2>&1" \
    > /etc/cron.d/torrentmonitor \
    && chmod 0644 /etc/cron.d/torrentmonitor

EXPOSE 80
