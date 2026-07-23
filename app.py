import os
import json
import requests
import numpy as np
from io import BytesIO
from PIL import Image
from flask import Flask, request, render_template, jsonify, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import tensorflow as tf

load_dotenv()

app = Flask(__name__)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

MODEL_PATH = "cropguard_model.h5"
CLASS_NAMES_PATH = "class_names.json"

print("Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH, "r") as f:
    CLASS_NAMES = json.load(f)

print(f"Model loaded. {len(CLASS_NAMES)} classes: {CLASS_NAMES}")

IMG_SIZE = (224, 224)

TREATMENT_ADVICE = {
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": (
        "Gray leaf spot is a fungal disease that spreads in warm, humid conditions. "
        "Remove infected leaves where possible. Apply a fungicide containing azoxystrobin or pyraclostrobin. "
        "Improve air circulation between plants by thinning if crops are dense."
    ),
    "Corn_(maize)___Common_rust_": (
        "Common rust spreads quickly in cool, moist weather. "
        "Apply a foliar fungicide such as mancozeb or propiconazole early. "
        "Rust-resistant varieties are the best long-term solution."
    ),
    "Corn_(maize)___Northern_Leaf_Blight": (
        "Northern leaf blight is a fungal infection causing long grey-green lesions. "
        "Apply fungicides at first sign of infection. "
        "Rotate crops each season and use resistant seed varieties where available."
    ),
    "Corn_(maize)___healthy": (
        "Your maize plant looks healthy. "
        "Keep monitoring regularly, ensure consistent watering, and watch for early signs of pest or disease pressure."
    ),
    "Grape___Black_rot": (
        "Black rot is a serious fungal disease that destroys fruit. "
        "Remove and destroy all infected plant material immediately. "
        "Apply captan or mancozeb fungicide and repeat every 7 to 10 days during wet weather."
    ),
    "Grape___Esca_(Black_Measles)": (
        "Esca is a complex wood disease with no reliable cure once established. "
        "Prune out and destroy infected wood during dry weather. "
        "Protect pruning wounds with a wound sealant to prevent re-infection."
    ),
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": (
        "Leaf blight causes brown spots and early leaf drop. "
        "Apply copper-based fungicides and remove infected leaves. "
        "Ensure good canopy ventilation by pruning regularly."
    ),
    "Grape___healthy": (
        "Your grapevine looks healthy. "
        "Continue regular monitoring, maintain good pruning practices, and ensure adequate drainage."
    ),
    "Pepper,_bell___Bacterial_spot": (
        "Bacterial spot spreads rapidly in warm, wet conditions. "
        "Apply copper-based bactericide immediately. "
        "Avoid overhead irrigation and handle plants only when dry to reduce spread."
    ),
    "Pepper,_bell___healthy": (
        "Your pepper plant looks healthy. "
        "Maintain consistent watering and watch for early signs of bacterial or fungal infection."
    ),
    "Potato___Early_blight": (
        "Early blight is a fungal disease causing dark spots with rings on older leaves. "
        "Apply chlorothalonil or mancozeb fungicide. "
        "Remove infected lower leaves and avoid wetting foliage when watering."
    ),
    "Potato___Late_blight": (
        "Late blight is a serious disease that can destroy an entire crop rapidly. "
        "Act immediately: apply metalaxyl or cymoxanil-based fungicide. "
        "Remove and destroy all infected plants. Do not compost infected material."
    ),
    "Potato___healthy": (
        "Your potato plant looks healthy. "
        "Monitor regularly, especially during wet weather when late blight risk is highest."
    ),
    "Tomato___Bacterial_spot": (
        "Bacterial spot causes small dark lesions on leaves and fruit. "
        "Apply copper hydroxide spray immediately. "
        "Remove infected leaves and avoid working with plants when they are wet."
    ),
    "Tomato___Early_blight": (
        "Early blight causes dark rings on lower leaves and spreads upward. "
        "Remove infected leaves, apply mancozeb or chlorothalonil fungicide. "
        "Water at the base of the plant rather than overhead."
    ),
    "Tomato___Late_blight": (
        "Late blight spreads very fast and can destroy your crop within days. "
        "Apply metalaxyl-based fungicide immediately. "
        "Remove and destroy all infected plant material. Do not leave debris in the field."
    ),
    "Tomato___Leaf_Mold": (
        "Leaf mold thrives in high humidity. "
        "Improve ventilation around your plants, reduce overhead watering. "
        "Apply a copper-based fungicide and remove heavily infected leaves."
    ),
    "Tomato___Septoria_leaf_spot": (
        "Septoria leaf spot spreads upward from older leaves. "
        "Remove infected leaves immediately and apply mancozeb or copper fungicide. "
        "Mulch around the base to prevent soil splash spreading the spores."
    ),
    "Tomato___Spider_mites Two-spotted_spider_mite": (
        "Spider mites cause yellowing and fine webbing on leaves. "
        "Spray plants with water to dislodge mites, then apply neem oil or insecticidal soap. "
        "Avoid using broad-spectrum insecticides which kill natural predators of mites."
    ),
    "Tomato___Target_Spot": (
        "Target spot causes circular lesions with rings, similar to early blight. "
        "Apply chlorothalonil or azoxystrobin fungicide. "
        "Remove heavily infected leaves and improve air circulation."
    ),
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": (
        "Yellow leaf curl virus is spread by whiteflies and has no cure once infected. "
        "Remove and destroy infected plants to protect surrounding crops. "
        "Control whitefly populations with yellow sticky traps and neem oil spray."
    ),
    "Tomato___Tomato_mosaic_virus": (
        "Tomato mosaic virus spreads through contact and has no cure. "
        "Remove infected plants immediately. Wash hands and tools thoroughly after handling. "
        "Use virus-resistant seed varieties in your next planting."
    ),
    "Tomato___healthy": (
        "Your tomato plant looks healthy. "
        "Keep monitoring regularly, water consistently at the base, and watch for early signs of disease."
    ),
}

BRAND_RECOMMENDATIONS = {
    "fungal": (
        "Recommended product: Dithane M-45 (Mancozeb) by Dow AgroSciences. "
        "Available at most agri-supply stores. Ask your local supplier for the correct dosage for your crop."
    ),
    "bacterial": (
        "Recommended product: Kocide 3000 (Copper Hydroxide) by FMC Corporation. "
        "Effective against bacterial infections. Available at agri-supply stores near you."
    ),
    "viral": (
        "No chemical cure for viral infections. "
        "Focus on removing infected plants and controlling the insects that spread the virus."
    ),
    "mite": (
        "Recommended product: Neem Oil Spray (organic option) or Abamectin-based miticide. "
        "Available at most agri-supply stores."
    ),
    "healthy": (
        "To keep your plants healthy: Yara fertilizers offer crop-specific nutrient programs. "
        "Ask your local agri-supplier about the right formula for your crop and soil type."
    ),
}

DISEASE_CATEGORY = {
    "Cercospora": "fungal", "rust": "fungal", "blight": "fungal",
    "Esca": "fungal", "Leaf_blight": "fungal", "mold": "fungal",
    "Septoria": "fungal", "Target_Spot": "fungal", "Black_rot": "fungal",
    "Bacterial": "bacterial", "mosaic_virus": "viral",
    "Yellow_Leaf_Curl_Virus": "viral", "Spider_mites": "mite",
    "healthy": "healthy",
}


def get_disease_category(class_name):
    for keyword, category in DISEASE_CATEGORY.items():
        if keyword.lower() in class_name.lower():
            return category
    return "fungal"


def preprocess_image(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE)
    arr = np.array(img) / 255.0
    return np.expand_dims(arr, axis=0)


def predict_disease(image_bytes):
    processed = preprocess_image(image_bytes)
    predictions = model.predict(processed, verbose=0)
    top_idx = int(np.argmax(predictions[0]))
    confidence = float(np.max(predictions[0])) * 100
    class_name = CLASS_NAMES[top_idx]
    return class_name, confidence


def format_diagnosis_reply(class_name, confidence):
    advice = TREATMENT_ADVICE.get(
        class_name,
        "No specific treatment advice available for this condition yet. "
        "Please consult your local agricultural extension officer."
    )
    category = get_disease_category(class_name)
    brand_rec = BRAND_RECOMMENDATIONS.get(category, "")
    display_name = class_name.replace("___", " - ").replace("_", " ")

    if "healthy" in class_name.lower():
        reply = (
            f"CropGuard AI Diagnosis\n"
            f"----------------------\n"
            f"Result: {display_name}\n"
            f"Confidence: {confidence:.1f}%\n\n"
            f"{advice}\n\n"
            f"{brand_rec}"
        )
    else:
        reply = (
            f"CropGuard AI Diagnosis\n"
            f"----------------------\n"
            f"Disease detected: {display_name}\n"
            f"Confidence: {confidence:.1f}%\n\n"
            f"Treatment:\n{advice}\n\n"
            f"{brand_rec}\n\n"
            f"Reply with any questions about this diagnosis and I will help you."
        )
    return reply


def answer_question(question):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "I can answer questions about crop diseases, treatment methods, "
            "and farming practices. For the best advice on your specific situation, "
            "please send a photo of the affected plant."
        )

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 300,
        "system": (
            "You are CropGuard AI, an agricultural assistant helping smallholder farmers "
            "in Africa and globally. Answer questions about crop diseases, treatment, "
            "planting, soil, and farming in simple, practical language. "
            "Keep answers under 200 words. Never recommend anything that requires "
            "expensive or unavailable equipment. Always suggest consulting a local "
            "agricultural extension officer for serious problems."
        ),
        "messages": [{"role": "user", "content": question}],
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=15
        )
        data = response.json()
        return data["content"][0]["text"]
    except Exception:
        return (
            "I could not process your question right now. "
            "Please try again or send a photo of your crop for a diagnosis."
        )


# PWA routes

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/diagnose", methods=["POST"])
def diagnose():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    image_bytes = file.read()

    try:
        class_name, confidence = predict_disease(image_bytes)
        advice = TREATMENT_ADVICE.get(
            class_name,
            "No specific treatment advice available for this condition yet. "
            "Please consult your local agricultural extension officer."
        )
        category = get_disease_category(class_name)
        recommendation = BRAND_RECOMMENDATIONS.get(category, "")
        display_name = class_name.replace("___", " - ").replace("_", " ")

        return jsonify({
            "disease": display_name,
            "confidence": round(confidence, 2),
            "treatment": advice,
            "recommendation": recommendation
        })

    except Exception as e:
        return jsonify({"error": "Could not process image. Please try again."}), 500


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please enter a question."}), 400

    answer = answer_question(question)
    return jsonify({"answer": answer})


# WhatsApp webhook

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))

    resp = MessagingResponse()
    msg = resp.message()

    if num_media > 0:
        media_url = request.form.get("MediaUrl0", "")
        try:
            image_response = requests.get(
                media_url,
                auth=(ACCOUNT_SID, AUTH_TOKEN),
                timeout=15
            )
            image_bytes = image_response.content
            class_name, confidence = predict_disease(image_bytes)
            reply = format_diagnosis_reply(class_name, confidence)
        except Exception:
            reply = (
                "Sorry, I could not process that image. "
                "Please make sure it is a clear photo of the affected leaf and try again."
            )
    elif incoming_msg:
        greetings = ["hi", "hello", "hey", "start", "help"]
        if incoming_msg.lower() in greetings:
            reply = (
                "Welcome to CropGuard AI.\n\n"
                "Send me a clear photo of your crop's affected leaf and I will "
                "identify the disease and tell you exactly how to treat it.\n\n"
                "You can also type any question about your crops and I will do my best to help.\n\n"
                "This service is completely free.\n\n"
                "You can also visit us at: https://cropguardai.app"
            )
        else:
            reply = answer_question(incoming_msg)
    else:
        reply = (
            "Send me a photo of your affected crop leaf for a diagnosis, "
            "or type a question about your crops. "
            "You can also visit cropguardai.app for our full web experience."
        )

    msg.body(reply)
    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)