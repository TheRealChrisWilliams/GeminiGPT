from flask import Flask, render_template, request, redirect, url_for

import google.generativeai as genai
import textwrap
from IPython.display import Markdown

import PIL.Image

import psycopg2

DB_HOST = "tiny.db.elephantsql.com"
DB_PORT = 5432
DB_NAME = "weczkopy"
DB_USER = "weczkopy"
DB_PASSWORD = ""

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

app = Flask(__name__, template_folder='templates')

GOOGLE_API_KEY = ''
genai.configure(api_key=GOOGLE_API_KEY)

responses = []

@app.route('/')
def index():
    # Fetch all chat records from the database
    with conn.cursor() as cursor:
        cursor.execute("SELECT user_text, chatbot_response FROM chats ORDER BY timestamp DESC")
        chat_records = cursor.fetchall()
        print(chat_records)

    return render_template('index.html', chat_records=chat_records)


@app.route('/process', methods=['POST'])
def process():
    prompt_text = request.form['prompt']
    prompt_image = request.files['image'] if 'image' in request.files else None

    if prompt_image:
        response = get_gemini_vision_response(prompt_text, prompt_image)
    else:
        response = get_gemini_response(prompt_text)

    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO chats (user_text, chatbot_response) VALUES (%s, %s)", (prompt_text, response))
        conn.commit()

    print("Gemini API Response:", response)

    return redirect(url_for('index'))


@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    # Clear chat records from the database
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM chats")
        conn.commit()

    # Clear chat records in the responses list
    responses.clear()

    return redirect(url_for('index'))


def get_gemini_response(prompt):
    def to_markdown(text):
        text = text.replace('•', '  *')
        return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return to_markdown(response.text).data

def get_gemini_vision_response(prompt, image):
    img = PIL.Image.open(image)

    print("Image Uploaded:", image.filename)

    # Set the model to gemini-pro-vision
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([prompt, img], stream=True)
    response.resolve()

    return response.text


if __name__ == '__main__':
    app.run(debug=True)
