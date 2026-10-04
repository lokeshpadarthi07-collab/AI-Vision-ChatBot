# 🥗 MacroSnap — AI Nutrition Buddy

MacroSnap is an AI-powered nutrition companion built with Streamlit, Gemini (Chat + Vision), and Twilio WhatsApp integration. 

Snap a photo of your meal or type a description, and MacroSnap provides instant calorie and macronutrient (protein, carbs, fat) estimates. When you're finished, a single click sends a complete, formatted summary straight to your WhatsApp!

---

## ✨ Features
- **Instant Photo Recognition**: Upload any meal photo (JPG/PNG) to get calorie and macronutrient breakdown.
- **Natural Conversational Chat**: Conversational AI powered by Google Gemini with contextual conversation memory.
- **Focused Nutrition Persona**: Strict guardrails ensure the bot politely focuses only on food, nutrition, fitness, and health.
- **WhatsApp Summary Dispatch**: Sends a clean running recap of all logged meals directly to WhatsApp via Twilio's Content API.
- **Zero Heavy ML Bloat**: Powered entirely by Gemini Vision and Twilio — no OpenCV, MediaPipe, or complex custom model training required.

---

## 🛠️ Project Structure
```text
macrosnap/
├── app.py                # Main Streamlit application
├── prompts.py            # AI personality, welcome, and summary prompts
├── requirements.txt      # Project dependencies
├── .gitignore            # Protects secrets and virtual environment
├── README.md             # Documentation and setup instructions
└── .streamlit/
    └── secrets.toml.example # Template for API credentials
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9 or newer installed
- Google AI Studio API Key ([Get API Key](https://aistudio.google.com))
- Twilio Account with WhatsApp Sandbox ([Twilio Console](https://www.twilio.com/try-twilio))

### 2. Setup Environment
Clone the repository and create a virtual environment:

```bash
# Clone repository
git clone <your-repo-link>
cd "AI Vision ChatBot"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (cmd.exe):
venv\Scripts\activate.bat
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Secrets
Create `.streamlit/secrets.toml` from the example template:

```bash
# Windows
copy .streamlit\secrets.toml.example .streamlit\secrets.toml

# macOS / Linux
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and fill in your credentials:
```toml
GEMINI_API_KEY = "AIzaSy..."
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
TWILIO_CONTENT_SID = "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

> **Twilio WhatsApp Setup Note:**
> 1. Join your Twilio WhatsApp Sandbox by texting your sandbox code (e.g. `join happy-tiger`) to `+14155238886`.
> 2. Create a Text Content Template in Twilio Console under **Messaging → Content Template Builder**:
>    - Body: `Hi {{1}}, here's your MacroSnap summary:\n\n{{2}}`
>    - Copy the generated Content SID (`HX...`) into your `secrets.toml`.

### 5. Run Locally
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deployment (Streamlit Community Cloud)
1. Push this project to your GitHub repository (verify `.streamlit/secrets.toml` is ignored).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Select your repository, branch (`main`), and set `app.py` as the entrypoint.
4. Go to **Settings → Secrets** in Streamlit Cloud, paste the contents of your `secrets.toml`, and click **Save**.
5. Click **Deploy** to get your public live URL!
