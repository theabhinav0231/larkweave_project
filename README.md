# Larkweave

# 🌐 Larkweave — Cross-Generation Knowledge Transfer Platform

✨ Demo

**🖥️ Deployed Application Link: https://larkweave.onrender.com**

📽️ Video Walkthrough: Watch here


**Empowering Wisdom. Connecting Generations. Powered by AI.**

Larkweave is a dynamic platform designed to bridge the generational gap through skill-sharing and mentorship. It allows experienced mentors to share real-world skills, knowledge, and creativity with younger learners through AI-enhanced content, community collaboration, and progress tracking.

Built during a 48-hour hackathon, Larkweave is more than just a project—it's a movement toward sustainable, cross-generational learning.

---

## 🚀 Project Overview

Larkweave connects mentors and learners through a seamless, AI-driven learning experience:

- Mentors upload short videos of skills or project demos.
- The system transcribes, summarizes, and generates structured learning content using **OpenAI Whisper** and **Google Gemma-3-27B-IT**.
- Learners engage with the material, upload progress, and receive real-time feedback.
- Final projects are showcased in a **Marketplace Gallery**, promoting visibility and appreciation.
- A community forum built with **Streamlit** fosters ongoing dialogue and peer learning.

> 🧠 “We believe knowledge is not just for passing down—but weaving across generations.”

---

## 🏆 Why This Project Matters
Cross-Generational Learning: Reviving forgotten skills by connecting generations.

Low Barrier for Entry: Simple YouTube video uploads and automatic content generation.

AI for Good: Ethical and empowering use of cutting-edge AI models.

Community-Driven: Learners and mentors engage, grow, and celebrate outcomes together.

## ⚙️ Key Features & Tech Stack

| Feature | Tech Used |
|--------|-----------|
| 🎥 Video Transcription | OpenAI Whisper |
| ✍️ AI Summary & Content Generation | Google Gemma-3-27B-IT |
| 📦 3D Model Generation | Dream Gaussian (HuggingFace) |
| 🔐 Authentication | Firebase OAuth |
| 🧠 Forum & Learner Progress UI | Streamlit |
| 🗃️ Database | Firebase Firestore |
| 🚀 Deployments | Render, Streamlit Community Cloud |
| 🌐 Frontend | HTML, CSS, JS |
| 🔁 Backend | Flask (Python) |

---

## 📦 Setup Instructions

> 🧪 Run the platform locally in just a few minutes!

### 🔧 Prerequisites
- Python 3.8+
- Node.js (for frontend if customizing)
- Firebase Project
- Huggingface Token
- Streamlit account

Made with passion during a 48-hour hackathon

### 🔌 1. Clone the repository

```bash
git clone https://github.com/theabhinav0231/Larkweave.git
cd larkweave

### 🐍 2. Backend (Flask)
cd backend
pip install -r requirements.txt
python app.py

### 🔐 3. Firebase Setup
Create a Firebase project.

Enable Authentication (Google).

Set up Firestore database.

Add your Firebase config to firebase_config.js and Flask environment.


### 🌐 4. Streamlit (Forum + Progress)
cd streamlit-app
streamlit run forum.py

### 5. Deployments
Flask Backend ➝ Render

Streamlit Apps ➝ Streamlit Community Cloud

Frontend ➝ Serve via Render or Vercel


