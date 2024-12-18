FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy necessary files into the container
COPY requirements.txt /app
COPY .env /app
COPY code /app/code

# Install the dependencies
RUN pip install -r requirements.txt

# Make ports available to the world outside this container
# FastAPI (8080) and Streamlit (8501)
EXPOSE 8080
EXPOSE 8501

# Run Python script
CMD ["python", "code/main.py"]
