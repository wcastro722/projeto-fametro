# Porto Digital em Flask

## Executar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

## Deploy no Railway

O projeto ja esta pronto para Railway com `Procfile` e `gunicorn`.

Comando usado no deploy:

```bash
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

Para subir no Git:

```bash
git init
git add .
git commit -m "Preparar deploy no Railway"
```

## Acesso inicial

- Usuario: `admin`
- Senha: `admin123`

## Funcionalidades

- Calendario semanal publico com barcos e lanchas
- Card de detalhes da viagem
- Botao de contato por WhatsApp
- Login de administrador
- Cadastro de viagens
# projeto-fametro
