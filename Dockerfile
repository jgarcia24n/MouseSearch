# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# You may define environment variables here or elsewhere
# You should replace these with your actual configuration at runtime
# ENV FLASK_SECRET_KEY="a-very-secret-key"
# ENV MAM_API_URL="https://www.myanonamouse.net"
# ENV QB_URL="http://localhost:8080"
# ENV QB_CATEGORY=""
# ENV QB_USERNAME="admin"
# ENV QB_PASSWORD=""
# ENV MAM_ID=""
# ENV MAM_UID=""
# ENV CF_ACCESS_CLIENT_ID=""
# ENV CF_ACCESS_CLIENT_SECRET=""

# Run app.py when the container launches
CMD ["python", "app.py", "--host=0.0.0.0"]