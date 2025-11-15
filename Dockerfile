FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir python-telegram-bot flask python-dotenv requests ccxt
CMD ["sh", "-c", "python web_ui.py & python nova_core.py"]
