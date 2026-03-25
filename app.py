import os
from flask import Flask
from dotenv import load_dotenv
from models import db

# Carrega as variáveis de segurança do arquivo .env
load_dotenv()

app = Flask(__name__)

# Puxa a URL do banco diretamente do .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Conecta o banco de dados ao nosso app
db.init_app(app)

# Cria as tabelas fisicamente lá no Neon
with app.app_context():
    db.create_all()
    print("Conectado ao Neon! Tabelas do Saideira criadas/verificadas com sucesso na nuvem.")

@app.route('/')
def home():
    return "Bem-vindo ao Saideira! O boteco tá aberto na nuvem."

if __name__ == '__main__':
    app.run(debug=True)