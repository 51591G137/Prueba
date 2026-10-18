from flask import Flask
app = Flask(__name__)

@app.route('/')
def inicio():
    return '¡El motor de mi app de restaurante está vivo!'
