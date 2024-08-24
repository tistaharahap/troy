FROM python:3.11-slim

WORKDIR /app
EXPOSE 8080

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Libmagic is required for python-magic
RUN apt-get update
RUN apt-get install -y locales build-essential
RUN set -ex \
    && ln -s /usr/include/locale.h /usr/include/xlocale.h
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
RUN rm -rf /var/lib/apt/lists/*

RUN --mount=source=dist,target=/dist pip install --no-cache-dir /dist/*.whl
RUN apt-get remove -y build-essential && apt-get autoremove -y

COPY pyproject.toml /app/pyproject.toml
COPY bin/run.sh /app/bin/run.sh
RUN chmod +x /app/bin/run.sh

CMD ["/app/bin/run.sh"]
