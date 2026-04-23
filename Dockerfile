FROM php:8.2-apache

RUN apt-get update && apt-get install -y \
        libcurl4-openssl-dev \
        libpq-dev \
        libsqlite3-dev \
        cron \
    && docker-php-ext-install curl pdo pdo_mysql pdo_pgsql pdo_sqlite \
    && rm -rf /var/lib/apt/lists/*

# Переключаем Apache с /var/www/html на /data/htdocs (совместимость с alfonder/torrentmonitor)
ENV APACHE_DOCUMENT_ROOT=/data/htdocs
RUN sed -i 's|/var/www/html|/data/htdocs|g' /etc/apache2/sites-available/000-default.conf \
    && sed -i 's|/var/www/html|/data/htdocs|g' /etc/apache2/apache2.conf \
    && sed -i 's|/var/www/html|/data/htdocs|g' /etc/apache2/conf-available/docker-php.conf

WORKDIR /data/htdocs

COPY . .

RUN cp config.php.example config.php \
    && chmod -R 755 /data/htdocs \
    && chown -R www-data:www-data /data/htdocs

# Cron для engine.php каждые 30 минут
RUN echo "*/30 * * * * www-data php /data/htdocs/engine.php >> /var/log/tm-engine.log 2>&1" \
    > /etc/cron.d/torrentmonitor \
    && chmod 0644 /etc/cron.d/torrentmonitor

EXPOSE 80
