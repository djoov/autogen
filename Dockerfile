# --- Single Stage Build is enough for Bytecode method ---
# Use Playwright image directly
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import autogen; print('✅ AutoGen installed successfully!')"

# Copy source code
COPY config.py .
COPY launcher.py .
COPY autobot.py .
COPY autobot2.py .
COPY bot_autogen.py .
COPY auto_hf.py .
COPY bot_silverbullet.py .
COPY bot_rag.py .
COPY bot_super.py .

# --- OBFUSCATION STEP (Bytecode Compilation) ---
# Compile ALL scripts to .pyc and remove .py files
RUN python -m compileall . && \
    cp __pycache__/config.*.pyc config.pyc && \
    cp __pycache__/launcher.*.pyc launcher.pyc && \
    cp __pycache__/autobot.*.pyc autobot.pyc && \
    cp __pycache__/autobot2.*.pyc autobot2.pyc && \
    cp __pycache__/bot_autogen.*.pyc bot_autogen.pyc && \
    cp __pycache__/auto_hf.*.pyc auto_hf.pyc && \
    cp __pycache__/bot_silverbullet.*.pyc bot_silverbullet.pyc && \
    cp __pycache__/bot_rag.*.pyc bot_rag.pyc && \
    cp __pycache__/bot_super.*.pyc bot_super.pyc && \
    rm *.py && \
    rm -rf __pycache__

# Set Entrypoint to run the LAUNCHER
ENTRYPOINT ["python", "launcher.pyc"]