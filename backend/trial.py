import google.generativeai as genai  # Import the Google Generative AI library
import os
from dotenv import load_dotenv

load_dotenv()
api = os.getenv("GOOGLE_API_KEY")
def main():
    # Configure the API key
    genai.configure(api_key=api)
    
    # Load the Gemini model (adjust model name if needed)
    model = genai.GenerativeModel("models/gemini-2.5-pro")
    
    # Your prompt to generate IEC 61131 Structured Text
    prompt = (
        "You are a PLC programming assistant.\n"
        "Generate an IEC 61131-3 Structured Text program that blinks a light every 1 second.\n"
        "Make sure the code is syntactically correct and ready to compile."
    )
    
    # Call the model to generate content
    response = model.generate_content(prompt)
    
    # Print the output from the model
    print("=== Generated IEC 61131-3 Structured Text Program ===")
    print(response.text)

if __name__ == "__main__":
    main()
