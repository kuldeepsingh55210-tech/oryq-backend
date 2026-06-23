# ORYQ Backend Deployment Guide (Railway)

This guide provides instructions to deploy the FastAPI backend of ORYQ to [Railway.app](https://railway.app).

## Prerequisites

1. A Railway account.
2. A Supabase project with rules and schema set up.
3. API credentials for Groq, Gemini, and OpenAI.

## Deployment Steps

1. **Push Code to GitHub**:
   Ensure your backend codebase is pushed to a repository on GitHub. Note that your Railway deploy will read directly from your repository.

2. **Create a New Project on Railway**:
   - Log in to Railway and click **New Project**.
   - Select **Deploy from GitHub repo** and choose your repository.
   - Set the root directory of your deploy to `backend` (if you are deploying from a monorepo) or let Railway detect your project structure.
   - Railway will automatically detect the `Procfile` in the backend folder and use it for the start command.

3. **Configure Environment Variables**:
   In the Railway dashboard under **Variables**, add the following settings:
   - `SUPABASE_URL`: Your Supabase Project API URL.
   - `SUPABASE_KEY`: Your Supabase Service Role Key or API Key.
   - `GROQ_API_KEY`: Your Groq API key (used for scans & hooks).
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
   - `OPENAI_API_KEY`: Your OpenAI API Key.
   - `ALLOWED_ORIGINS`: A comma-separated list of allowed origins. You should set this to:
     `http://localhost:3000,https://your-frontend-vercel-domain.vercel.app` (replace with your actual Vercel deployment URL once generated).

4. **Verify Deployment**:
   - Once deployed, Railway will generate a public URL (e.g. `https://backend-production-xxx.up.railway.app`).
   - Open `<railway-url>/health` in your browser. It should return:
     ```json
     {"status": "healthy", "service": "oryq-backend"}
     ```
   - Copy this URL—you will need to provide it as the `NEXT_PUBLIC_API_URL` variable in your frontend Vercel deployment.
