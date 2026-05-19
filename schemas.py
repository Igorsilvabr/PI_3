from pydantic import BaseModel
from typing import Optional

# ── SCHEMAS DE ANIMAL ─────────────────────────────────
class AnimalCreate(BaseModel):
    nome:    str
    especie: str
    raca:    str
    idade:   int
    dono:    str
    sexo:    Optional[str] = "Não informado"

class AnimalResponse(BaseModel):
    id: int
    nome: str
    especie: str
    raca: str
    idade: int
    dono: str
    sexo: Optional[str] = "Não informado"
    prontuario: Optional[str] = ""

    model_config = {"from_attributes": True}

# ── SCHEMAS DE TUTOR ──────────────────────────────────
class TutorCreate(BaseModel):
    nome:     str
    telefone: str
    cpf:      Optional[str] = None
    email:    Optional[str] = None
    endereco: Optional[str] = None
    pets:     str = "Nenhum"

class TutorResponse(TutorCreate):
    id: int
    model_config = {"from_attributes": True}

# ── SCHEMAS DE VETERINÁRIO ────────────────────────────
class VeterinarioCreate(BaseModel):
    nome:          str
    especialidade: str
    telefone:      str
    crmv:          Optional[str] = None

class VeterinarioResponse(VeterinarioCreate):
    id: int
    model_config = {"from_attributes": True}

# ── SCHEMAS DE SERVIÇO ────────────────────────────────
class ServicoCreate(BaseModel):
    nome:      str
    categoria: str
    valor:     float

class ServicoResponse(ServicoCreate):
    id: int
    model_config = {"from_attributes": True}

# ── SCHEMAS DE AGENDAMENTO ────────────────────────────
class AgendamentoCreate(BaseModel):
    horario:     str
    nome_pet:    str
    motivo:      str
    veterinario: str
    status:      str = "agendado"
    observacoes: str = ""

class AgendamentoResponse(AgendamentoCreate):
    id: int
    model_config = {"from_attributes": True}