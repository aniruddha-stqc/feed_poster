import google.generativeai as genai

API_KEY = "AIzaSyAH711_bskCn_LA-bCPSJIVsDW6DYX9Xsc"

genai.configure(api_key=API_KEY)

print("google-generativeai version:", genai.__version__)
print("Listing models...")

for m in genai.list_models():
    print(m.name)
