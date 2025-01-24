from flask import Flask, render_template, request
import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials

# 1. Ustawienia Azure Computer Vision
ENDPOINT = "https://image-description-service.cognitiveservices.azure.com/"  # Zamień na swój endpoint
KEY = "Br0TIBOK3gl4TteDG7ikR0rrfM5GojBVICujvzYCzhhl4LDHeOssJQQJ99BAAC5RqLJXJ3w3AAAFACOGXat7"  # Zamień na swój klucz API

# 2. Autoryzacja klienta
client = ComputerVisionClient(ENDPOINT, CognitiveServicesCredentials(KEY))

# Tworzenie aplikacji Flask
app = Flask(__name__)

# Ustawienie folderu na przesyłane obrazy
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 3. Główna trasa
@app.route("/", methods=["GET", "POST"])
def index():
    description = None
    colors = None
    extracted_text = None
    image_filename = None

    if request.method == "POST":
        # Pobierz przesłany obraz
        file = request.files["image"]
        if file:
            # Zapisz obraz do folderu static/uploads
            image_filename = file.filename
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)
            file.save(image_path)

            # Otwórz obraz i przekaż do analiz
            try:
                # 1. Generowanie opisu
                with open(image_path, "rb") as image_stream:
                    description_result = client.describe_image_in_stream(image_stream)

                # 2. Analiza kolorów
                with open(image_path, "rb") as image_stream:
                    color_analysis_result = client.analyze_image_in_stream(
                        image_stream, visual_features=["Color"]
                    )

                # 3. Rozpoznawanie tekstu (OCR)
                with open(image_path, "rb") as image_stream:
                    ocr_result = client.read_in_stream(image_stream, raw=True)
                    operation_location = ocr_result.headers["Operation-Location"]
                    operation_id = operation_location.split("/")[-1]

                    # Poczekaj na zakończenie operacji OCR
                    result = client.get_read_result(operation_id)
                    while result.status in ["notStarted", "running"]:
                        import time
                        time.sleep(1)
                        result = client.get_read_result(operation_id)

                    # Wyodrębnij tekst z wyniku OCR
                    if result.status == "succeeded":
                        extracted_text = "\n".join(
                            line.text for read_result in result.analyze_result.read_results
                            for line in read_result.lines
                        )
                    else:
                        extracted_text = "Nie udało się odczytać tekstu."

                # Wyodrębnij opis
                if description_result.captions:
                    description = description_result.captions[0].text
                else:
                    description = "Nie wygenerowano opisu."

                # Wyodrębnij analizę kolorów
                if color_analysis_result.color:
                    colors = {
                        "dominant_background_color": color_analysis_result.color.dominant_color_background,
                        "dominant_foreground_color": color_analysis_result.color.dominant_color_foreground,
                        "dominant_colors": color_analysis_result.color.dominant_colors,
                        "is_bw": color_analysis_result.color.is_bw_img,
                    }
            except Exception as e:
                description = "Wystąpił błąd podczas analizy obrazu."
                colors = None
                extracted_text = None
                print(f"Błąd: {e}")

    return render_template(
        "index.html",
        description=description,
        colors=colors,
        extracted_text=extracted_text,
        image_filename=image_filename,
    )


if __name__ == "__main__":
    app.run(debug=True)
