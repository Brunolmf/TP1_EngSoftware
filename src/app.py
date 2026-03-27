import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
from models import db, Usuario
import re

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

@app.route('/acesso', methods=['GET', 'POST'])
def acesso():
    erro = None
    sucesso = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        if not email or not senha:
            erro = 'Preencha email e senha.'
        else:
            usuario = Usuario.query.filter_by(email=email).first()

            if not usuario:
                erro = 'Email ou senha invalidos.'
            elif not usuario.verificar_senha(senha):
                erro = 'Email ou senha invalidos.'
            else:
                sucesso = f'Login validado para {usuario.nome}. O proximo passo sera criar a sessao.'
        

    return render_template('acesso.html', erro=erro, sucesso=sucesso)

def email_valido(email):
    padrao = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(padrao, email) is not None

def senha_forte(senha):
    if (len(senha) < 8):
        return False
    tem_maiuscula = any(c.isupper() for c in senha)
    tem_minuscula = any(c.islower() for c in senha)
    tem_numero = any(c.isdigit() for c in senha)
    tem_especial = any(not c.isalnum() for c in senha)
    return tem_especial and tem_maiuscula and  tem_minuscula and tem_numero

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
        elif not email_valido(email):
            erro = 'Digite um email valido.'
        elif Usuario.query.filter_by(email=email).first():
            erro = 'Este email ja esta cadastrado.'
        elif not senha_forte(senha):
            erro = 'A senha deve ter pelo menos 8 caracteres, com letra maiuscula, minuscula, numero e caractere especial.'
        
        else:
            try:
                idade = int(idade_texto)
                if idade < 0 or idade > 120:
                    erro = "Digite uma idade válida"
                elif idade < 18:
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
