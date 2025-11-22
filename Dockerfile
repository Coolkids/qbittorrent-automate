FROM python:3.14-slim

WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"

COPY ./ /app/

RUN apt-get update -y \
    && apt-get upgrade -y \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && pip install --no-cache-dir --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ \
    && pip install pipx -i https://mirrors.aliyun.com/pypi/simple/ \
    && pipx install poetry \
    && cd /app \
    && poetry install

CMD ["poetry", "run", "python", "src/qbittorrent-automate/main.py"]
