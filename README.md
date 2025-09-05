# PSU-Menu-Analyzer

Penn State Altoona Menu Analyzer Web App
This web application provides personalized dining recommendations for the Penn State Altoona campus cafeteria, Port Sky Cafe. It scrapes the daily menu, analyzes food items based on user preferences (vegetarian, dietary exclusions, protein priority), and provides a ranked list of suggestions.

Features
User Preferences: Toggle options for vegetarian, exclude beef, exclude pork, and high-protein priority.

Dynamic Scraping: Fetches the menu for the current day directly from the PSU dining website.

Dual Analysis Modes:

Local Analysis: A rule-based system scores food based on keywords.

AI-Powered Analysis: (Optional) Uses the Google Gemini API for more nuanced, context-aware recommendations.

Modern UI: A clean, responsive, and mobile-friendly interface built with Tailwind CSS.

How It Works
The application is composed of two main parts:

Frontend (index.html): A single HTML file containing the user interface, styling, and client-side JavaScript. It captures user preferences and makes an API call to the backend.

Backend (main.py): A Python server built with Flask. It exposes a single API endpoint (/api/analyze) that receives the user's preferences, runs the MenuAnalyzer class, and returns the recommendations as JSON.

The entire application is designed to be containerized with Docker, making it easy to deploy to virtually any cloud hosting provider.

Local Development
To run this application on your local machine, follow these steps.

Prerequisites
Python 3.7+ installed

pip for package management

Setup
Clone the repository or save the files:
Make sure you have index.html, main.py, requirements.txt, and Dockerfile in the same directory.

Create a virtual environment (Recommended):

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

Install dependencies:

pip install -r requirements.txt

(Optional) Set Gemini API Key:
To use the AI analysis feature, you need to set your Gemini API key as an environment variable.

# On macOS/Linux
export GEMINI_API_KEY="YOUR_API_KEY_HERE"

# On Windows (Command Prompt)
set GEMINI_API_KEY="YOUR_API_KEY_HERE"

If you don't set this, the app will gracefully fall back to the local, rule-based analysis.

Run the backend server:

flask run --port 5001

The backend will now be running at http://127.0.0.1:5001.

Open the frontend:
Open the index.html file directly in your web browser. The JavaScript is configured to send requests to your local backend. Enter your preferences and click "Analyze Today's Menu".

Deployment to the Cloud (Google Cloud Run)
Deploying this app to the web is straightforward using Google Cloud Run, which has a generous free tier suitable for this project.

Prerequisites
A Google Cloud Platform (GCP) account.

The gcloud command-line tool installed and authenticated.

Docker installed on your local machine.

Step-by-Step Deployment
Enable GCP APIs:
In the GCP Console, enable the Cloud Run API and Artifact Registry API for your project.

Create an Artifact Registry Repository:
This is where you'll store your Docker image.

gcloud artifacts repositories create menu-analyzer-repo --repository-format=docker --location=us-central1 --description="Docker repository for Menu Analyzer"

(You can replace us-central1 with a region near you.)

Configure Docker Authentication:
Allow Docker to push images to your new repository.

gcloud auth configure-docker us-central1-docker.pkg.dev

Build the Docker Image:
From your project directory (containing the Dockerfile), run the following command. Replace YOUR_GCP_PROJECT_ID with your actual project ID.

docker build -t us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/menu-analyzer-repo/menu-app:latest .

Push the Image to Artifact Registry:

docker push us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/menu-analyzer-repo/menu-app:latest

Deploy to Cloud Run:
This final command deploys your container and makes it public.

gcloud run deploy menu-analyzer-app \
  --image us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/menu-analyzer-repo/menu-app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars=GEMINI_API_KEY="YOUR_API_KEY_HERE"

--allow-unauthenticated: Makes the website public.

--set-env-vars: This is the secure way to provide your API key. It injects it as an environment variable that only the server can access.

Done!
The command will output a URL (e.g., https://menu-analyzer-app-....a.run.app). This is the public address for your website! Visit it in your browser to use your live application.