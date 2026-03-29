import google.generativeai as genai
import os
import sys

# Set the key directly
os.environ['GOOGLE_API_KEY'] = 'AIzaSyBEU8wP_-LG73__vxf6sROk7eeuhukomT4'

key = os.environ.get("GOOGLE_API_KEY")

if key:
    print(f"[KEY] Loaded: {key[:20]}...")
else:
    print("[ERROR] NO KEY FOUND")
    sys.exit(1)

try:
    print("[INFO] Configuring API...")
    genai.configure(api_key=key)

    print("[INFO] Creating model...")
    model = genai.GenerativeModel("gemini-2.0-flash")

    print("[INFO] Testing API call...")
    response = model.generate_content("Say 'TEST_PASSED' only")

    print("[SUCCESS] API KEY IS VALID AND WORKING!")
    print(f"Response: {response.text}")

except Exception as e:
    print("[ERROR] API KEY FAILED!")
    print(f"Error: {str(e)}")
    sys.exit(1)
