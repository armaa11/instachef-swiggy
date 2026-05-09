# Online Deployment Guide: Mise En Place

To deploy this application online, you need to host three components:
1. **Frontend**: Next.js App
2. **Backend**: FastAPI Application
3. **Database**: Redis

The recommended free/low-cost stack is:
- **Vercel** for the Frontend
- **Render** or **Railway** for the Backend
- **Upstash** or **Render** for Redis

Here is the step-by-step guide to deploying each part.

---

## 1. Deploy the Database (Redis)

Using **Upstash** (Serverless Redis, generous free tier) or **Render** Redis.
1. Create a free account at [Upstash](https://upstash.com/).
2. Create a new Redis database.
3. Copy the **Redis URL** (it looks like `rediss://default:PASSWORD@endpoint.upstash.io:PORT`).

*(Keep this URL handy; you will need it for the Backend).*

---

## 2. Deploy the Backend (FastAPI)

I have created a `Dockerfile` in the `backend/` directory to make deploying the backend very easy. We recommend **Render** or **Railway**.

### Option A: Using Render (Free tier available)
1. Push your code to a GitHub repository.
2. Sign up at [Render](https://render.com/).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Provide the following settings:
   - **Root Directory**: `backend`
   - **Environment**: `Docker` (Render will automatically detect the Dockerfile we just created).
   - **Branch**: `main`
6. Click **Advanced** and add your Environment Variables:
   - `REDIS_URL` = (The URL you got from Upstash)
   - `OPENAI_API_KEY` = (Your OpenAI key)
   - `ANTHROPIC_API_KEY` = (Your Anthropic key)
   - `SWIGGY_CLIENT_ID` = ...
   - `SWIGGY_CLIENT_SECRET` = ...
   - Any other secrets listed in your backend `.env`
7. Click **Create Web Service**.
8. Once deployed, Render will give you a public URL (e.g., `https://mise-backend.onrender.com`).

*(Keep this URL handy; you will need it for the Frontend).*

---

## 3. Deploy the Frontend (Next.js)

**Vercel** is the creators of Next.js and provides the best hosting for it.

1. Create a free account at [Vercel](https://vercel.com/) and connect your GitHub.
2. Click **Add New** -> **Project**.
3. Import your GitHub repository.
4. Set the **Root Directory** to `frontend`.
5. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL` = (The URL of your backend from Render, e.g., `https://mise-backend.onrender.com`)
6. Click **Deploy**.

---

## 4. Final Verification
- Once Vercel finishes deploying, visit your new public URL.
- Try submitting a recipe video to ensure the Next.js frontend can successfully reach your FastAPI backend, and that your backend is properly communicating with Upstash Redis and the AI APIs.

### Note on CORS
If your Vercel URL is blocked by CORS on the backend, ensure your backend's `app/main.py` explicitly allows the Vercel production URL in the `CORSMiddleware` origins list:
```python
origins = [
    "http://localhost:3000",
    "https://your-vercel-project-url.vercel.app" # Add your Vercel URL here
]
```
