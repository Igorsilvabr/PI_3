from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base

class Animal(Base):
    __tablename__ = "animais"
    id          = Column(Integer, primary_key=True, index=True)
    nome        = Column(String, nullable=False)
    especie     = Column(String, nullable=False)
    raca        = Column(String)
    idade       = Column(Integer)
    dono        = Column(String, nullable=False)  # nome do tutor
    sexo        = Column(String, default="Não informado")
    prontuario  = Column(String, default="")  # <-- Adicionado para persistir as notas médicas do pet

class Tutor(Base):
    __tablename__ = "tutores"
    id       = Column(Integer, primary_key=True, index=True)
    nome     = Column(String, nullable=False)
    cpf      = Column(String)
    telefone = Column(String)
    email    = Column(String)
    endereco = Column(String)
    pets     = Column(String, default="Nenhum")

class Veterinario(Base):
    __tablename__ = "veterinarios"
    id            = Column(Integer, primary_key=True, index=True)
    nome          = Column(String, nullable=False)
    crmv          = Column(String)
    especialidade = Column(String)
    telefone      = Column(String)

class Servico(Base):
    __tablename__ = "servicos"
    id        = Column(Integer, primary_key=True, index=True)
    nome      = Column(String, nullable=False)
    categoria = Column(String)
    valor     = Column(Float, nullable=False)

class Agendamento(Base):
    __tablename__ = "agendamentos"
    id          = Column(Integer, primary_key=True, index=True)
    horario     = Column(String, nullable=False)
    nome_pet    = Column(String, nullable=False)
    motivo      = Column(String)
    veterinario = Column(String)
    status      = Column(String, default="agendado")
    observacoes = Column(String, default="")

class Funcionario(Base):
    __tablename__ = "funcionarios"
    id    = Column(Integer, primary_key=True, index=True)
    nome  = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)  # Armazenará o hash seguro da senha