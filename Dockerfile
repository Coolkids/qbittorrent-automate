FROM python:3.14-slim

WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"

ADD ./ /app/

RUN apt-get update -y \
    && apt-get upgrade -y \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && pip install --no-cache-dir --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ \
    && pip install pipx -i https://mirrors.aliyun.com/pypi/simple/ \
    && pipx install poetry \
    && cd /app \
    && poetry install

CMD ["poetry", "run", "python", "src/qibttorrent-automate/main.py"]
