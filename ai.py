import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyDMTxFGXbzIdpCD_MhY4qWc2gRSpqEG1Yg"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def get_chatbot_response(message):
    try:
        response = model.generate_content(message)
        return response.text.strip()
    except Exception as e:
        return f"[No response from Gemini: {e}]"