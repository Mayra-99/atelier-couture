# Image de l'API : Python 3.12 (version imposée), légère ("slim")
FROM python:3.12-slim

# Pas de fichiers .pyc, logs affichés tout de suite
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /code

# 1) On installe d'abord les bibliothèques (étape mise en cache par Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Puis on copie le code
COPY . .

EXPOSE 8000

# Au démarrage : crée/met à jour les tables (Alembic), remplit la base (seed), lance l'API
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
