import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
from models import db, Usuario

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
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    sucesso = None

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        idade_texto = request.form.get('idade', '').strip()

        if not nome or not email or not senha or not idade_texto:
            erro = 'Preencha todos os campos.'
        elif Usuario.query.filter_by(email=email).first():
            erro = 'Este email ja esta cadastrado.'
        else:
            try:
                idade = int(idade_texto)
                if idade < 18:
                    erro = 'Voce precisa ter pelo menos 18 anos para criar uma conta.'
            except ValueError:
                erro = 'Digite uma idade valida.'
            else:
                usuario = Usuario(
                    nome=nome,
                    email=email,
                    idade=idade
                )
                usuario.set_senha(senha)

                db.session.add(usuario)
                db.session.commit()
                sucesso = 'Conta criada com sucesso.'

    return render_template('cadastro.html', erro=erro, sucesso=sucesso)

if __name__ == '__main__':
    app.run(debug=True)
