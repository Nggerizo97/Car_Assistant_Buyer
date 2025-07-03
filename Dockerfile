# Use the official Python image as the base
FROM python:3.10-slim-bullseye

# Update system packages to reduce vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies
RUN playwright install
# Copy the entire project into the container
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=True

# Expose any necessary ports (if applicable)
EXPOSE 8501

# Command to run both the scraper and Streamlit app
CMD ["sh", "-c", "python src/scraper/main_scraper.py & streamlit run src/streamlit_app.py --server.port=8501 --server.address=0.0.0.0"]