import os
import sys
import random
from datetime import datetime, timezone

# Adiciona a pasta 'src' ao path do sistema para conseguirmos importar a aplicação
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app import app
from models import db, Estabelecimento, Usuario, Avaliacao

def seed_avaliacoes():
    with app.app_context():
        # 1. Pega até 3 bares do banco
        bares = Estabelecimento.query.limit(3).all()
        
        if not bares:
            print("Nenhum estabelecimento encontrado no banco. Por favor, adicione bares primeiro.")
            return

        # 2. Verifica se tem algum usuário para ser o autor, senão cria um de teste
        usuario = Usuario.query.first()
        if not usuario:
            usuario = Usuario(
                nome="Usuário Teste", 
                email="teste@teste.com", 
                idade=25
            )
            usuario.set_senha("teste123")
            db.session.add(usuario)
            db.session.commit()
            print("Usuário de teste criado.")

        textos_reviews = [
            "Excelente lugar, cerveja bem gelada e o petisco estava maravilhoso!",
            "O ambiente é legal, mas o atendimento demorou um pouco.",
            "Um dos meus bares favoritos em BH. Voltarei sempre que puder."
        ]

        avaliacoes_criadas = 0

        # 3. Cria uma avaliação para cada um dos 3 bares
        for i, bar in enumerate(bares):
            nova_avaliacao = Avaliacao(
                nota=round(random.uniform(3.0, 5.0), 1), # Nota geral entre 3.0 e 5.0
                texto_review=textos_reviews[i % len(textos_reviews)],
                avaliacao_comida=round(random.uniform(3.5, 5.0), 1),
                avaliacao_bebida=round(random.uniform(4.0, 5.0), 1),
                usuario_id=usuario.id,
                estabelecimento_id=bar.id
            )
            db.session.add(nova_avaliacao)
            avaliacoes_criadas += 1

        try:
            db.session.commit()
            print(f"Sucesso! {avaliacoes_criadas} avaliações inseridas nos seguintes bares:")
            for bar in bares:
                print(f"- {bar.nome}")
        except Exception as e:
            db.session.rollback()
            print("Erro ao tentar inserir avaliações:", e)

if __name__ == '__main__':
    seed_avaliacoes()
