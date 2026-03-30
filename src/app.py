import os
import re
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from models import db, Usuario, Estabelecimento, Avaliacao
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)

# Configurações de Segurança
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# A SECRET_KEY é necessária para usar session
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'boteco_secreto_123')

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    bares_query = db.session.query(
        Estabelecimento,
        func.avg(Avaliacao.nota).label('media_notas')
    ).outerjoin(Avaliacao).group_by(Estabelecimento.id).order_by(func.avg(Avaliacao.nota).desc().nulls_last()).all()
    
    bares_destaque = []
    outros_bares = []
    
    for bar, media in bares_query:
        bar_dict = {
            'nome': bar.nome,
            'endereco': bar.endereco,
            'foto_url': bar.foto_url,
            'nota': round(media, 1) if media else 'Sem nota'
        }
        if media:
            bares_destaque.append(bar_dict)
        else:
            outros_bares.append(bar_dict)
            
    return render_template('index.html', bares_destaque=bares_destaque, outros_bares=outros_bares)

@app.route('/acesso', methods=['GET', 'POST'])
def acesso():
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        if not email or not senha:
            erro = 'Preencha email e senha.'
        else:
            usuario = Usuario.query.filter_by(email=email).first()
            if usuario and usuario.verificar_senha(senha):
                # Cria a sessão do usuário
                session['usuario_id'] = usuario.id
                session['usuario_nome'] = usuario.nome
                return redirect(url_for('home'))
            else:
                erro = 'Email ou senha inválidos.'

    return render_template('acesso.html', erro=erro)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        idade_texto = request.form.get('idade', '').strip()

        if not nome or not email or not senha or not idade_texto:
            erro = 'Preencha todos os campos.'
        elif Usuario.query.filter_by(email=email).first():
            erro = 'Este email já está cadastrado.'
        else:
            try:
                idade = int(idade_texto)
                if idade < 18:
                    erro = 'Você precisa ter pelo menos 18 anos.'
                else:
                    novo_usuario = Usuario(nome=nome, email=email, idade=idade)
                    novo_usuario.set_senha(senha)
                    db.session.add(novo_usuario)
                    db.session.commit()
                    
                    # Login automático após cadastro
                    session['usuario_id'] = novo_usuario.id
                    session['usuario_nome'] = novo_usuario.nome
                    return redirect(url_for('home'))
            except ValueError:
                erro = 'Idade inválida.'

    return render_template('cadastro.html', erro=erro)

@app.route('/sair')
def sair():
    session.clear() # Limpa os dados da sessão
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)