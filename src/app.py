import os
import re
import math
import time
from flask import flash 
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from models import db, Usuario, Estabelecimento, Avaliacao
from sqlalchemy import func
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)

# Configurações de Segurança
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'boteco_secreto_123')

db.init_app(app)

with app.app_context():
    db.create_all()
    db.session.execute(text(
        "ALTER TABLE avaliacoes "
        "ADD COLUMN IF NOT EXISTS avaliacao_ambiente FLOAT"
    ))
    db.session.execute(text(
        "ALTER TABLE avaliacoes "
        "ADD COLUMN IF NOT EXISTS avaliacao_servico FLOAT"
    ))
    db.session.commit()

@app.route('/')
def home():
    termo_busca = request.args.get('q', '').strip()

    # paginação de bares
    page = request.args.get('page', 1, type=int)
    per_page = 12

    # Busca o objeto do usuário logado para verificar se é admin no template
    usuario_logado = None
    if 'usuario_id' in session:
        usuario_logado = Usuario.query.get(session['usuario_id'])

    # Base da query com a média
    query = db.session.query(
        Estabelecimento,
        func.avg(Avaliacao.nota).label('media_notas')
    ).outerjoin(Avaliacao)

    if termo_busca:
        busca = f"%{termo_busca}%"
        query = query.filter(Estabelecimento.nome.ilike(busca))

    bares_query = query.group_by(Estabelecimento.id).order_by(func.avg(Avaliacao.nota).desc().nulls_last()).all()
    
    bares_destaque = []
    outros_bares = []
    
    for bar, media in bares_query:
        bar_dict = {
            'id': bar.id,
            'nome': bar.nome,
            'endereco': bar.endereco,
            'foto_url': bar.foto_url,
            'nota': round(media, 1) if media else 'Sem nota'
        }
        
        if media:
            bares_destaque.append(bar_dict)
        else:
            outros_bares.append(bar_dict)

    total_outros = len(outros_bares)
    total_pages = (total_outros + per_page - 1) // per_page 

    inicio = (page - 1) * per_page
    fim = inicio + per_page
    outros_bares_paginados = outros_bares[inicio:fim]
            
    return render_template('index.html', 
                           bares_destaque=bares_destaque, 
                           outros_bares=outros_bares_paginados, 
                           termo_busca=termo_busca,
                           usuario_logado=usuario_logado,
                           page=page,
                           total_pages=total_pages)

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
                session['usuario_id'] = usuario.id
                session['usuario_nome'] = usuario.nome
                return redirect(url_for('home'))
            else:
                erro = 'Email ou senha inválidos.'

    return render_template('acesso.html', erro=erro)

@app.route('/perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        idade_texto = request.form.get('idade', '').strip()
        nova_senha = request.form.get('senha', '')

        if not nome or not email or not idade_texto:
            flash('Campos obrigatórios não preenchidos.', 'erro')
            return redirect(url_for('editar_perfil'))

        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente and usuario_existente.id != usuario.id:
            flash('Este email já está em uso.', 'erro')
            return redirect(url_for('editar_perfil'))

        try:
            usuario.nome = nome
            usuario.email = email
            usuario.idade = int(idade_texto)
            
            if nova_senha:
                usuario.set_senha(nova_senha)

            db.session.commit()
            session['usuario_nome'] = usuario.nome
            flash('Perfil atualizado com sucesso!', 'sucesso')
            return redirect(url_for('editar_perfil'))
            
        except Exception:
            db.session.rollback()
            flash('Erro ao atualizar perfil.', 'erro')
            return redirect(url_for('editar_perfil'))

    avaliacoes_usuario = Avaliacao.query.filter_by(usuario_id=usuario.id).order_by(
        Avaliacao.data_avaliacao.desc()
    ).all()

    media_usuario = None
    if avaliacoes_usuario:
        media_usuario = round(
            sum(avaliacao.nota for avaliacao in avaliacoes_usuario) / len(avaliacoes_usuario),
            1
        )

    return render_template(
        'perfil.html',
        usuario=usuario,
        avaliacoes_usuario=avaliacoes_usuario,
        media_usuario=media_usuario
    )

@app.route('/bar/adicionar', methods=['GET', 'POST'])
def adicionar_bar():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'erro')
        return redirect(url_for('acesso'))
    
    usuario = Usuario.query.get(session['usuario_id'])
    
    if not getattr(usuario, 'is_admin', False):
        flash('Acesso negado: apenas administradores podem adicionar bares.', 'erro')
        return redirect(url_for('home'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        endereco = request.form.get('endereco', '').strip()
        foto_url = request.form.get('foto_url', '').strip()
        faixa_de_preco = request.form.get('faixa_de_preco', '$')
        # A LINHA DA DESCRICAO FOI REMOVIDA DAQUI

        if not nome or not endereco:
            flash('Nome e Endereço são campos obrigatórios.', 'erro')
            return redirect(url_for('adicionar_bar'))

        try:
            novo_bar = Estabelecimento(
                nome=nome, 
                endereco=endereco, 
                foto_url=foto_url,
                faixa_de_preco=faixa_de_preco,
                adicionado_por=usuario.id
            )
            # A LINHA QUE TENTAVA SALVAR A DESCRICAO FOI REMOVIDA
            
            db.session.add(novo_bar)
            db.session.commit()
            flash(f'Boteco "{nome}" cadastrado com sucesso!', 'sucesso')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Erro técnico ao salvar no banco de dados.', 'erro')
            return redirect(url_for('adicionar_bar'))

    return render_template('adicionar_bar.html')

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
                elif idade >= 125:
                    erro = 'Digite uma idade válida.'
                else:
                    novo_usuario = Usuario(nome=nome, email=email, idade=idade)
                    novo_usuario.set_senha(senha)
                    db.session.add(novo_usuario)
                    db.session.commit()
                    
                    session['usuario_id'] = novo_usuario.id
                    session['usuario_nome'] = novo_usuario.nome
                    return redirect(url_for('home'))
            except ValueError:
                erro = 'Idade inválida.'

    return render_template('cadastro.html', erro=erro)

@app.route('/sair')
def sair():
    session.clear() 
    return redirect(url_for('home'))

@app.route('/bar/<int:bar_id>', methods=['GET'])
def detalhes_bar(bar_id):
    bar = Estabelecimento.query.get_or_404(bar_id)
    avaliacoes = Avaliacao.query.filter_by(estabelecimento_id=bar_id).order_by(
        Avaliacao.nota.desc(),
        Avaliacao.data_avaliacao.desc()
    ).all()
    
    return render_template('bar.html', bar=bar, avaliacoes=avaliacoes)

@app.route('/bar/<int:bar_id>/avaliar', methods=['POST'])
def avaliar_bar(bar_id):
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    bar = Estabelecimento.query.get_or_404(bar_id)
    texto_review = request.form.get('texto_review')
    avaliacao_bebida = request.form.get('avaliacao_bebida', type=float)
    avaliacao_comida = request.form.get('avaliacao_comida', type=float)
    avaliacao_ambiente = request.form.get('avaliacao_ambiente', type=float)
    avaliacao_servico = request.form.get('avaliacao_servico', type=float)
    
    categorias = [
        avaliacao_bebida,
        avaliacao_comida,
        avaliacao_ambiente,
        avaliacao_servico
    ]

    if any(nota is None for nota in categorias):
        return redirect(url_for('detalhes_bar', bar_id=bar_id))

    nota = round(sum(categorias) / len(categorias), 1)

    nova_avaliacao = Avaliacao(
        nota=nota,
        texto_review=texto_review,
        avaliacao_comida=avaliacao_comida,
        avaliacao_bebida=avaliacao_bebida,
        avaliacao_ambiente=avaliacao_ambiente,
        avaliacao_servico=avaliacao_servico,
        usuario_id=session['usuario_id'],
        estabelecimento_id=bar.id
    )
    
    db.session.add(nova_avaliacao)
    db.session.commit()
    
    return redirect(url_for('detalhes_bar', bar_id=bar_id))

@app.route('/admin/usuarios')
def admin_usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    usuario_logado = Usuario.query.get(session['usuario_id'])
    if not usuario_logado or not usuario_logado.is_admin:
        flash('Acesso negado.')
        return redirect(url_for('home'))

    # Lista todos os usuários exceto o próprio admin logado (opcional)
    todos_usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template('admin_usuarios.html', usuarios=todos_usuarios, usuario_logado=usuario_logado)

@app.route('/admin/usuarios/deletar/<int:id>', methods=['POST'])
def deletar_usuario(id):
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    admin = Usuario.query.get(session['usuario_id'])
    if not admin or not admin.is_admin:
        flash('Operação não permitida.')
        return redirect(url_for('home'))

    usuario_para_deletar = Usuario.query.get_or_404(id)

    # Impede que um admin delete a si mesmo ou outro admin por engano (regra de segurança)
    if usuario_para_deletar.is_admin:
        flash('Não é possível remover um administrador.')
        return redirect(url_for('admin_usuarios'))

    try:
        db.session.delete(usuario_para_deletar)
        db.session.commit()
        flash(f'Usuário {usuario_para_deletar.nome} removido com sucesso!', 'sucesso')
    except Exception:
        db.session.rollback()
        flash('Erro ao remover usuário.')

    return redirect(url_for('admin_usuarios'))

if __name__ == '__main__':
    app.run(debug=True)
