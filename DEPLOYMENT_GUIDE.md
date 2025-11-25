# Streamlit Cloud Deployment Guide

## Step 1: Push to GitHub

Make sure your code is pushed to GitHub (without `.env` or `secrets.toml`).

## Step 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Select your GitHub repository
4. Set main file: `app.py`
5. Click "Advanced settings"

## Step 3: Add Secrets

In the "Secrets" section, paste this:

```toml
# Add your API keys here (get them from https://console.groq.com)
GROQ_API_KEY_1 = "your_first_groq_api_key_here"
GROQ_API_KEY_2 = "your_second_groq_api_key_here"
GROQ_API_KEY_3 = "your_third_groq_api_key_here"

GROQ_MODEL = "llama-3.1-8b-instant"
LLM_PROVIDER = "groq"
```

## Step 4: Deploy

Click "Deploy" and wait for the app to start!

## For Local Development

The app will automatically use `.streamlit/secrets.toml` or `.env` file for local testing.

## Troubleshooting

If you see "No API keys configured":
1. Check that secrets are added in Streamlit Cloud dashboard
2. Restart the app
3. Check logs for any import errors
