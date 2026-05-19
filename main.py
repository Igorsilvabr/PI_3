from fastapi.staticfiles import StaticFiles  
import bcrypt
from fastapi import FastAPI, Depends, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional  
import models, schemas
from database import engine, SessionLocal
import secrets

# Cria as tabelas no banco de dados automaticamente se não existirem
models.Base.metadata.create_all(bind=engine)

# INSTÂNCIA ÚNICA DO FASTAPI
app = FastAPI(title="Clínica Veterinária")

# Ativa a pasta de arquivos estáticos (Imagens, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# ── Sessões em memória ─────────────────────────────────
sessoes_ativas = set()

# ── Credenciais demo (Dicionário estático mantido) ─────
USUARIOS = {
    "admin": "1234",
    "vitoria": "vet2025",
}

# ── Schema de login ────────────────────────────────────
class LoginData(BaseModel):
    usuario: str
    senha: str

# ── Schema auxiliar de cadastro de funcionário ─────────
class FuncionarioCadastro(BaseModel):
    nome: str
    email: str
    senha: str

# ── Verificar se está logado ───────────────────────────
def verificar_sessao(request: Request):
    token = request.cookies.get("sessao")
    if not token or token not in sessoes_ativas:
        return False
    return True

# ── Banco de dados ─────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Rota: página de login ──────────────────────────────
@app.get("/", response_class=HTMLResponse)
def pagina_login(request: Request):
    if verificar_sessao(request):
        return RedirectResponse(url="/sistema")
    return templates.TemplateResponse(request=request, name="login.html")

# ── Rota: processar login (UNIFICADA E INTEGRADA) ──────
@app.post("/login")
def fazer_login(dados: LoginData, response: Response, db: Session = Depends(get_db)):
    funcionario = db.query(models.Funcionario).filter(models.Funcionario.email == dados.usuario).first()
    
    if funcionario:
        senha_correta = bcrypt.checkpw(
            dados.senha.encode('utf-8'), 
            funcionario.senha.encode('utf-8')
        )
        if not senha_correta:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
    else:
        senha_estatica = USUARIOS.get(dados.usuario)
        if not senha_estatica or senha_estatica != dados.senha:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    token = secrets.token_hex(32)
    sessoes_ativas.add(token)
    
    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        key="sessao",
        value=token,
        httponly=True,
        max_age=3600 * 8  # 8 horas
    )
    return response

# ── Rota: sistema principal (protegida) ────────────────
@app.get("/sistema", response_class=HTMLResponse)
def pagina_sistema(request: Request):
    if not verificar_sessao(request):
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="index.html")

# ── Rota: logout ───────────────────────────────────────
@app.get("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("sessao")
    if token:
        sessoes_ativas.discard(token)
    resp = RedirectResponse(url="/")
    resp.delete_cookie("sessao")
    return resp

# ── Animais ────────────────────────────────────────────
# ROTA CORRIGIDA: Criação flexível de animais para evitar travamentos do botão Salvar (Erro 422)
@app.post("/animais/")
def criar_animal(request: Request, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    
    # Validação simples para garantir que o nome foi preenchido
    if not dados.get("nome"):
        raise HTTPException(status_code=400, detail="O nome do animal é obrigatório.")
        
    # Tratamento seguro da idade (converte para inteiro se enviado como string)
    idade_valor = dados.get("idade")
    try:
        idade_final = int(idade_valor) if idade_valor is not None else 0
    except (ValueError, TypeError):
        idade_final = 0

    obj = models.Animal(
        nome=dados.get("nome"),
        especie=dados.get("especie"),
        raca=dados.get("raca"),
        idade=idade_final,
        dono=dados.get("dono"),
        sexo=dados.get("sexo", "Não informado"),
        prontuario=dados.get("prontuario", "")
    )
    
    db.add(obj)
    db.commit()
    db.refresh(obj)
    
    return {
        "id": obj.id,
        "nome": obj.nome,
        "especie": obj.especie,
        "raca": obj.raca,
        "idade": obj.idade,
        "dono": obj.dono,
        "sexo": obj.sexo,
        "prontuario": obj.prontuario
    }


@app.get("/animais/", response_model=list[schemas.AnimalResponse])
def listar_animais(request: Request, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    return db.query(models.Animal).all()

@app.get("/animais/{animal_id}")
def obter_animal(request: Request, animal_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    
    obj = db.get(models.Animal, animal_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Animal não encontrado")
        
    return {
        "id": obj.id,
        "nome": obj.nome,
        "especie": obj.especie,
        "raca": obj.raca,
        "idade": obj.idade,
        "dono": obj.dono,
        "sexo": obj.sexo if obj.sexo else "Não informado",
        "prontuario": obj.prontuario if obj.prontuario else ""
    }

# ROTA CORRIGIDA: Atualização de Prontuário via Parâmetro URL (Alinhado com o Front-end)
@app.put("/animais/{animal_id}/prontuario")
def atualizar_prontuario_animal(request: Request, animal_id: int, prontuario: str, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    
    obj = db.get(models.Animal, animal_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Animal não encontrado")
        
    obj.prontuario = prontuario
    db.commit()
    return {"ok": True}

@app.put("/animais/{animal_id}")
def atualizar_animal(request: Request, animal_id: int, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
        
    obj = db.get(models.Animal, animal_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Animal não encontrado")
    
    obj.nome = dados.get("nome", obj.nome)
    obj.especie = dados.get("especie", obj.especie)
    obj.raca = dados.get("raca", obj.raca)
    obj.idade = int(dados.get("idade", obj.idade))
    obj.dono = dados.get("dono", obj.dono)
    obj.sexo = dados.get("sexo", obj.sexo)

    db.commit()
    return {"ok": True}

@app.delete("/animais/{animal_id}")
def deletar_animal(request: Request, animal_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Animal, animal_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Animal não encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}

# ── Tutores ────────────────────────────────────────────
@app.post("/tutores/", response_model=schemas.TutorResponse)
def criar_tutor(request: Request, tutor: schemas.TutorCreate, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = models.Tutor(**tutor.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.get("/tutores/", response_model=list[schemas.TutorResponse])
def listar_tutores(request: Request, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    return db.query(models.Tutor).all()

@app.get("/tutores/{tutor_id}", response_model=schemas.TutorResponse)
def obter_tutor(request: Request, tutor_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Tutor, tutor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tutor não encontrado")
    return obj

@app.put("/tutores/{tutor_id}")
def atualizar_tutor(request: Request, tutor_id: int, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Tutor, tutor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tutor não encontrado")
    
    obj.nome = dados.get("nome", obj.nome)
    obj.cpf = dados.get("cpf", obj.cpf)
    obj.telefone = dados.get("telefone", obj.telefone)
    obj.email = dados.get("email", obj.email)
    obj.endereco = dados.get("endereco", obj.endereco)
    obj.pets = dados.get("pets", obj.pets)
    
    db.commit()
    return {"ok": True}

@app.delete("/tutores/{tutor_id}")
def deletar_tutor(request: Request, tutor_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Tutor, tutor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tutor não encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}

# ── Veterinários ───────────────────────────────────────
@app.post("/veterinarios/", response_model=schemas.VeterinarioResponse)
def criar_veterinario(request: Request, vet: schemas.VeterinarioCreate, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = models.Veterinario(**vet.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.get("/veterinarios/", response_model=list[schemas.VeterinarioResponse])
def listar_veterinarios(request: Request, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    return db.query(models.Veterinario).all()

@app.get("/veterinarios/{vet_id}", response_model=schemas.VeterinarioResponse)
def obter_veterinario(request: Request, vet_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Veterinario, vet_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Veterinário não encontrado")
    return obj

@app.put("/veterinarios/{vet_id}")
def atualizar_veterinario(request: Request, vet_id: int, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Veterinario, vet_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Veterinário não encontrado")
    
    obj.nome = dados.get("nome", obj.nome)
    obj.crmv = dados.get("crmv", obj.crmv)
    obj.especialidade = dados.get("especialidade", obj.especialidade)
    obj.telefone = dados.get("telefone", obj.telefone)
    
    db.commit()
    return {"ok": True}

@app.delete("/veterinarios/{vet_id}")
def deletar_veterinario(request: Request, vet_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Veterinario, vet_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Veterinário não encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}

# ── Serviços ───────────────────────────────────────────
@app.post("/servicos/", response_model=schemas.ServicoResponse)
def criar_servico(request: Request, servico: schemas.ServicoCreate, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = models.Servico(**servico.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.get("/servicos/", response_model=list[schemas.ServicoResponse])
def listar_servicos(request: Request, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    return db.query(models.Servico).all()

@app.get("/servicos/{servico_id}", response_model=schemas.ServicoResponse)
def obter_servico(request: Request, servico_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Servico, servico_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return obj

@app.put("/servicos/{servico_id}")
def atualizar_servico(request: Request, servico_id: int, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Servico, servico_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    obj.nome = dados.get("nome", obj.nome)
    obj.categoria = dados.get("categoria", obj.categoria)
    obj.valor = float(dados.get("valor", obj.valor))
    
    db.commit()
    return {"ok": True}

@app.delete("/servicos/{servico_id}")
def deletar_servico(request: Request, servico_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Servico, servico_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}

# ── Agendamentos ───────────────────────────────────────
@app.post("/agendamentos/", response_model=schemas.AgendamentoResponse)
def criar_agendamento(request: Request, agenda: schemas.AgendamentoCreate, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = models.Agendamento(**agenda.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@app.get("/agendamentos/", response_model=list[schemas.AgendamentoResponse])
def listar_agendamentos(request: Request, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    return db.query(models.Agendamento).all()

# ROTA CORRIGIDA: Adicionada a rota específica para atualização de status via URL Parameter
@app.put("/agendamentos/{agenda_id}/status")
def atualizar_status_agendamento(request: Request, agenda_id: int, status: str, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Agendamento, agenda_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    obj.status = status
    db.commit()
    return {"ok": True}

@app.put("/agendamentos/{agenda_id}")
def atualizar_agendamento(request: Request, agenda_id: int, dados: dict, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Agendamento, agenda_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    obj.horario = dados.get("horario", obj.horario)
    obj.nome_pet = dados.get("nome_pet", obj.nome_pet)
    obj.motivo = dados.get("motivo", obj.motivo)
    obj.veterinario = dados.get("veterinario", obj.veterinario)
    obj.observacoes = dados.get("observacoes", obj.observacoes)
    obj.status = dados.get("status", obj.status)
        
    db.commit()
    return {"ok": True}

@app.delete("/agendamentos/{agenda_id}")
def deletar_agendamento(request: Request, agenda_id: int, db: Session = Depends(get_db)):
    if not verificar_sessao(request):
        raise HTTPException(status_code=401, detail="Não autorizado")
    obj = db.get(models.Agendamento, agenda_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}

# ── Rota: página de cadastro ───────────────────────────
@app.get("/cadastro", response_class=HTMLResponse)
def pagina_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="cadastro.html")

# ── Rota: processar cadastro de funcionário ────────────────
@app.post("/cadastrar")
def cadastrar_funcionario(funcionario: FuncionarioCadastro, db: Session = Depends(get_db)):
    usuario_existe = db.query(models.Funcionario).filter(models.Funcionario.email == funcionario.email).first()
    if usuario_existe:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")
    
    senha_bytes = funcionario.senha.encode('utf-8')
    sal = bcrypt.gensalt()
    senha_criptografada = bcrypt.hashpw(senha_bytes, sal).decode('utf-8')
    
    novo_func = models.Funcionario(
        nome=funcionario.nome,
        email=funcionario.email,
        senha=senha_criptografada
    )
    
    db.add(novo_func)
    db.commit()
    return {"ok": True, "detail": "Funcionário cadastrado com sucesso!"}