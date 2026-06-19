import math
import os

from flask import flash
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from sqlalchemy import func, inspect, text

try:
    from .models import db, Usuario, Estabelecimento, Avaliacao
except ImportError:
    from models import db, Usuario, Estabelecimento, Avaliacao

load_dotenv()

def _get_database_uri():
    return os.getenv('DATABASE_URL', 'sqlite:///saideira.db')


def _initialize_database():
    db.create_all()

    inspector = inspect(db.engine)
    if 'avaliacoes' not in inspector.get_table_names():
        return

    colunas_existentes = {
        coluna['name'] for coluna in inspector.get_columns('avaliacoes')
    }
    colunas_opcionais = {
        'avaliacao_ambiente': 'FLOAT',
        'avaliacao_servico': 'FLOAT',
    }

    alteracoes_pendentes = []
    for nome_coluna, tipo_coluna in colunas_opcionais.items():
        if nome_coluna not in colunas_existentes:
            alteracoes_pendentes.append(
                text(f'ALTER TABLE avaliacoes ADD COLUMN {nome_coluna} {tipo_coluna}')
            )

    if not alteracoes_pendentes:
        return

    for alteracao in alteracoes_pendentes:
        db.session.execute(alteracao)

    db.session.commit()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=_get_database_uri(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY', 'boteco_secreto_123'),
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    register_routes(app)

    with app.app_context():
        _initialize_database()

    return app

def home():
    termo_busca = request.args.get('q', '').strip()

    # paginação de bares
    page = request.args.get('page', 1, type=int)
    per_page = 12

    # Busca o objeto do usuário logado para verificar se é admin no template
    usuario_logado = None
    if 'usuario_id' in session:
        usuario_logado = db.session.get(Usuario, session['usuario_id'])

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

def editar_perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    usuario = db.session.get(Usuario, session['usuario_id'])
    
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
            idade = int(idade_texto)
        except ValueError:
            flash('Idade inválida.', 'erro')
            return redirect(url_for('editar_perfil'))

        if idade < 18:
            flash('Você precisa ter pelo menos 18 anos.', 'erro')
            return redirect(url_for('editar_perfil'))

        if idade >= 125:
            flash('Digite uma idade válida.', 'erro')
            return redirect(url_for('editar_perfil'))

        try:
            usuario.nome = nome
            usuario.email = email
            usuario.idade = idade
            
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

def adicionar_bar():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'erro')
        return redirect(url_for('acesso'))
    
    usuario = db.session.get(Usuario, session['usuario_id'])
    
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

def sair():
    session.clear() 
    return redirect(url_for('home'))

def detalhes_bar(bar_id):
    bar = db.get_or_404(Estabelecimento, bar_id)
    avaliacoes = Avaliacao.query.filter_by(estabelecimento_id=bar_id).order_by(
        Avaliacao.nota.desc(),
        Avaliacao.data_avaliacao.desc()
    ).all()
    
    return render_template('bar.html', bar=bar, avaliacoes=avaliacoes)

def avaliar_bar(bar_id):
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    bar = db.get_or_404(Estabelecimento, bar_id)
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

    if any(not math.isfinite(nota) or nota < 0.5 or nota > 5.0 for nota in categorias):
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

def admin_usuarios():
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    usuario_logado = db.session.get(Usuario, session['usuario_id'])
    if not usuario_logado or not usuario_logado.is_admin:
        flash('Acesso negado.')
        return redirect(url_for('home'))

    # Lista todos os usuários exceto o próprio admin logado (opcional)
    todos_usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template('admin_usuarios.html', usuarios=todos_usuarios, usuario_logado=usuario_logado)

def deletar_usuario(id):
    if 'usuario_id' not in session:
        return redirect(url_for('acesso'))
    
    admin = db.session.get(Usuario, session['usuario_id'])
    if not admin or not admin.is_admin:
        flash('Operação não permitida.')
        return redirect(url_for('home'))

    usuario_para_deletar = db.get_or_404(Usuario, id)

    # Impede que um admin delete a si mesmo ou outro admin por engano (regra de segurança)
    if usuario_para_deletar.is_admin:
        flash('Não é possível remover um administrador.')
        return redirect(url_for('admin_usuarios'))

    try:
        Estabelecimento.query.filter_by(adicionado_por=usuario_para_deletar.id).update(
            {'adicionado_por': None},
            synchronize_session=False
        )
        db.session.delete(usuario_para_deletar)
        db.session.commit()
        flash(f'Usuário {usuario_para_deletar.nome} removido com sucesso!', 'sucesso')
    except Exception:
        db.session.rollback()
        flash('Erro ao remover usuário.')

    return redirect(url_for('admin_usuarios'))


def register_routes(app):
    app.add_url_rule('/', view_func=home)
    app.add_url_rule('/acesso', view_func=acesso, methods=['GET', 'POST'])
    app.add_url_rule('/perfil', view_func=editar_perfil, methods=['GET', 'POST'])
    app.add_url_rule('/bar/adicionar', view_func=adicionar_bar, methods=['GET', 'POST'])
    app.add_url_rule('/cadastro', view_func=cadastro, methods=['GET', 'POST'])
    app.add_url_rule('/sair', view_func=sair)
    app.add_url_rule('/bar/<int:bar_id>', view_func=detalhes_bar, methods=['GET'])
    app.add_url_rule('/bar/<int:bar_id>/avaliar', view_func=avaliar_bar, methods=['POST'])
    app.add_url_rule('/admin/usuarios', view_func=admin_usuarios)
    app.add_url_rule(
        '/admin/usuarios/deletar/<int:id>',
        view_func=deletar_usuario,
        methods=['POST'],
    )


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
