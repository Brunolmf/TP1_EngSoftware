from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializa o banco de dados (vamos conectar ele ao Flask depois)
db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False) #bruno lembrar de colocar salt
    is_admin = db.Column(db.Boolean, default=False)
    idade = db.Column(db.Integer, nullable=False)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relacionamento: Um usuário possui várias avaliações (lista de objetos 'Avaliacao')
    avaliacoes = db.relationship('Avaliacao', backref='autor', lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Estabelecimento(db.Model):
    __tablename__ = 'estabelecimentos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    foto_url = db.Column(db.String(255), nullable=True)
    faixa_de_preco = db.Column(db.String(50), nullable=True) # Ex: $, $$, $$$
    
    # Quem cadastrou este bar? (Referencia o ID na tabela de usuarios)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamento: Um estabelecimento possui várias avaliações
    avaliacoes = db.relationship('Avaliacao', backref='bar', lazy=True)

    def __repr__(self):
        return f'<Estabelecimento {self.nome}>'

class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    nota = db.Column(db.Float, nullable=False) # Ex: 1 a 5 estrelas
    texto_review = db.Column(db.Text, nullable=True)
    avaliacao_comida = db.Column(db.Float, nullable=True) # Ex: 1.0 a 5.0
    avaliacao_bebida = db.Column(db.Float, nullable=True) # Ex: 1.0 a 5.0
    data_avaliacao = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Chaves Estrangeiras conectando a avaliação ao usuário e ao bar
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    estabelecimento_id = db.Column(db.Integer, db.ForeignKey('estabelecimentos.id'), nullable=False)

    def __repr__(self):
        return f'<Avaliacao {self.nota} estrelas do Usuario {self.usuario_id}>'
