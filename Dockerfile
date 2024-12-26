FROM debian:12-slim
RUN apt-get update && apt-get install -y python3 python3-venv python3-dev gcc
WORKDIR /root/pipe
COPY console ./console
COPY core ./core
COPY database ./database
COPY models ./models
COPY utils ./utils
COPY loader.py ./loader.py
COPY requirements.txt ./requirements.txt
COPY run.py ./run.py
COPY run.sh ./run.sh
COPY setup.sh ./setup.sh

RUN chmod -R 777 /root/pipe
RUN ./setup.sh
ENTRYPOINT ["./run.sh", "farm"]