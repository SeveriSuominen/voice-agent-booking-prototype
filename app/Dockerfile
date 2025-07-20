# ---------------------------------------------- #
#                      client                    #
# ---------------------------------------------- #

FROM python:3.13-slim
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin-$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 3000

CMD ["python", "app.py"]


