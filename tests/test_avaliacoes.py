from src.models import Avaliacao, Estabelecimento, db


def login(client, usuario_id):
    with client.session_transaction() as sessao:
        sessao['usuario_id'] = usuario_id


def criar_bar(app, nome='Boteco do Zé', endereco='Rua A, 123'):
    with app.app_context():
        bar = Estabelecimento(nome=nome, endereco=endereco)
        db.session.add(bar)
        db.session.commit()
        return bar.id


def notas_validas(**overrides):
    dados = {
        'texto_review': 'Lugar ótimo!',
        'avaliacao_bebida': '5.0',
        'avaliacao_comida': '4.0',
        'avaliacao_ambiente': '4.0',
        'avaliacao_servico': '3.0',
    }
    dados.update(overrides)
    return dados


# ---------------------------------------------------------------------------
# /bar/<id> (detalhes_bar)
# ---------------------------------------------------------------------------

def test_detalhes_bar_mostra_estabelecimento(client, app):
    bar_id = criar_bar(app, nome='Bar Visível')

    resposta = client.get(f'/bar/{bar_id}')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Bar Visível' in corpo


def test_detalhes_bar_inexistente_retorna_404(client):
    resposta = client.get('/bar/9999')

    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# /bar/<id>/avaliar (avaliar_bar)
# ---------------------------------------------------------------------------

def test_avaliar_bar_exige_login(client, app):
    bar_id = criar_bar(app)

    resposta = client.post(f'/bar/{bar_id}/avaliar', data=notas_validas())

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/acesso')


def test_avaliar_bar_inexistente_retorna_404(client, criar_usuario):
    usuario = criar_usuario(email='avaliador@teste.com')
    login(client, usuario['id'])

    resposta = client.post('/bar/9999/avaliar', data=notas_validas())

    assert resposta.status_code == 404


def test_avaliar_bar_cria_avaliacao_com_media_correta(client, app, criar_usuario):
    usuario = criar_usuario(email='avaliador@teste.com')
    bar_id = criar_bar(app)
    login(client, usuario['id'])

    resposta = client.post(f'/bar/{bar_id}/avaliar', data=notas_validas())

    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith(f'/bar/{bar_id}')

    with app.app_context():
        avaliacao = Avaliacao.query.filter_by(estabelecimento_id=bar_id).first()
        assert avaliacao is not None
        # média de 5 + 4 + 4 + 3 = 16 / 4 = 4.0
        assert avaliacao.nota == 4.0
        assert avaliacao.usuario_id == usuario['id']


def test_avaliar_bar_ignora_categoria_faltando(client, app, criar_usuario):
    usuario = criar_usuario(email='avaliador@teste.com')
    bar_id = criar_bar(app)
    login(client, usuario['id'])

    dados = notas_validas()
    del dados['avaliacao_servico']

    resposta = client.post(f'/bar/{bar_id}/avaliar', data=dados)

    assert resposta.status_code == 302
    with app.app_context():
        assert Avaliacao.query.count() == 0


def test_avaliar_bar_rejeita_nota_fora_do_intervalo(client, app, criar_usuario):
    usuario = criar_usuario(email='avaliador@teste.com')
    bar_id = criar_bar(app)
    login(client, usuario['id'])

    resposta = client.post(
        f'/bar/{bar_id}/avaliar',
        data=notas_validas(avaliacao_bebida='9.0'),
    )

    assert resposta.status_code == 302
    with app.app_context():
        assert Avaliacao.query.count() == 0


# ---------------------------------------------------------------------------
# / (home) — destaque vs. sem nota e busca
# ---------------------------------------------------------------------------

def test_home_separa_bares_com_e_sem_nota(client, app, criar_usuario):
    usuario = criar_usuario(email='avaliador@teste.com')
    bar_avaliado = criar_bar(app, nome='Bar Avaliado')
    criar_bar(app, nome='Bar Sem Nota')
    login(client, usuario['id'])
    client.post(f'/bar/{bar_avaliado}/avaliar', data=notas_validas())

    resposta = client.get('/')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Bar Avaliado' in corpo
    assert 'Bar Sem Nota' in corpo


def test_home_filtra_por_termo_de_busca(client, app):
    criar_bar(app, nome='Cervejaria Central')
    criar_bar(app, nome='Pizzaria da Praça')

    resposta = client.get('/?q=Cervejaria')
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert 'Cervejaria Central' in corpo
    assert 'Pizzaria da Praça' not in corpo
