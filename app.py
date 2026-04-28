from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "porto_digital.db"

DAY_NAMES = {
    0: "Segunda",
    1: "Terca",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sabado",
    6: "Domingo",
}

MONTH_NAMES = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}

ADMIN_USER = "admin"
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-flask-porto-digital")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS viagens_semanais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            capacidade INTEGER NOT NULL,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            dia_semana INTEGER NOT NULL,
            horario_saida TEXT NOT NULL,
            horario_chegada TEXT NOT NULL,
            chegada_dia_offset INTEGER NOT NULL DEFAULT 0,
            descricao TEXT,
            telefone_contato TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def seed_demo_data() -> None:
    db = sqlite3.connect(DATABASE)
    total = db.execute("SELECT COUNT(*) FROM viagens_semanais").fetchone()[0]
    if total:
        db.close()
        return

    demo_viagens = [
        ("Barco Rio Negro", "Barco", 180, "Parintins", "Manaus", 0, "07:00", "18:30", 2),
        ("Lancha Expresso Segunda", "Lancha", 36, "Itacoatiara", "Manaus", 0, "14:00", "17:00", 0),
        ("Barco Ajuricaba", "Barco", 160, "Manacapuru", "Manaus", 1, "06:45", "10:20", 1),
        ("Lancha Expresso Terca", "Lancha", 34, "Novo Airao", "Manaus", 1, "14:00", "17:00", 0),
        ("Barco Estrela do Norte", "Barco", 140, "Careiro", "Manaus", 2, "07:15", "09:50", 0),
        ("Lancha Expresso Quarta", "Lancha", 32, "Iranduba", "Manaus", 2, "14:00", "17:00", 0),
        ("Barco Princesa do Rio", "Barco", 200, "Autazes", "Manaus", 3, "06:20", "13:40", 2),
        ("Lancha Expresso Quinta", "Lancha", 30, "Itapiranga", "Manaus", 3, "14:00", "17:00", 0),
        ("Barco Sol do Amazonas", "Barco", 170, "Borba", "Manaus", 4, "07:10", "16:20", 0),
        ("Lancha Expresso Sexta", "Lancha", 38, "Silves", "Manaus", 4, "14:00", "17:00", 0),
        ("Barco Navegante", "Barco", 150, "Codajas", "Manaus", 5, "08:00", "18:00", 0),
        ("Lancha Expresso Sabado", "Lancha", 28, "Barreirinha", "Manaus", 5, "14:00", "17:00", 0),
        ("Barco Encontro das Aguas", "Barco", 155, "Maues", "Manaus", 6, "07:30", "19:00", 0),
        ("Lancha Expresso Domingo", "Lancha", 35, "Presidente Figueiredo", "Manaus", 6, "14:00", "17:00", 0),
    ]

    db.executemany(
        """
        INSERT INTO viagens_semanais
        (nome, tipo, capacidade, origem, destino, dia_semana, horario_saida, horario_chegada,
         chegada_dia_offset, descricao, telefone_contato)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                nome,
                tipo,
                capacidade,
                origem,
                destino,
                dia_semana,
                horario_saida,
                horario_chegada,
                chegada_offset,
                "Viagem recorrente da grade semanal com embarque organizado no porto.",
                "92999990000" if tipo == "Barco" else "92988880000",
            )
            for (
                nome,
                tipo,
                capacidade,
                origem,
                destino,
                dia_semana,
                horario_saida,
                horario_chegada,
                chegada_offset,
            ) in demo_viagens
        ],
    )
    db.commit()
    db.close()


def admin_logged_in() -> bool:
    return bool(session.get("admin_logado"))


def require_admin():
    if not admin_logged_in():
        return redirect(url_for("login"))
    return None


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date_br(value: str) -> str:
    current = parse_date(value)
    return f"{current.day:02d} {MONTH_NAMES[current.month]}"


def format_full_date_br(value: str) -> str:
    current = parse_date(value)
    return f"{DAY_NAMES[current.weekday()]}, {current.day:02d} {MONTH_NAMES[current.month]}"


def weekday_name_from_date(value: str) -> str:
    return DAY_NAMES[parse_date(value).weekday()]


def format_time_br(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        parsed = datetime.strptime(value, "%H:%M:%S")
    return parsed.strftime("%H:%M")


def start_of_week(today: date | None = None, week_offset: int = 0) -> date:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=week_offset)


def list_rotas_semanais() -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        """
        SELECT *
        FROM viagens_semanais
        ORDER BY dia_semana ASC, horario_saida ASC, nome ASC
        """
    ).fetchall()


def build_week_days(week_offset: int) -> list[dict[str, Any]]:
    start = start_of_week(week_offset=week_offset)
    days = []
    for offset in range(7):
        current = start + timedelta(days=offset)
        days.append(
            {
                "date": current.isoformat(),
                "label": DAY_NAMES[current.weekday()],
                "day": f"{current.day:02d}",
                "month": MONTH_NAMES[current.month],
                "weekday": current.weekday(),
            }
        )
    return days


def build_week_instances(week_offset: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    days = build_week_days(week_offset)
    week_dates = {day["weekday"]: day["date"] for day in days}
    instances: list[dict[str, Any]] = []

    for rota in list_rotas_semanais():
        saida_data = parse_date(week_dates[int(rota["dia_semana"])])
        chegada_data = saida_data + timedelta(days=int(rota["chegada_dia_offset"]))

        instances.append(
            {
                "id": int(rota["id"]),
                "nome": rota["nome"],
                "tipo": rota["tipo"],
                "capacidade": int(rota["capacidade"]),
                "origem": rota["origem"],
                "destino": rota["destino"],
                "data_saida": saida_data.isoformat(),
                "data_chegada": chegada_data.isoformat(),
                "horario_saida": rota["horario_saida"],
                "horario_chegada": rota["horario_chegada"],
                "descricao": rota["descricao"],
                "telefone_contato": rota["telefone_contato"],
                "dia_semana": int(rota["dia_semana"]),
                "saida_label": DAY_NAMES[saida_data.weekday()],
                "chegada_label": DAY_NAMES[chegada_data.weekday()],
            }
        )

    instances.sort(key=lambda item: (item["data_saida"], item["horario_saida"], item["nome"]))
    return days, instances


def count_by_day(viagens: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in viagens:
        counts[item["data_saida"]] = counts.get(item["data_saida"], 0) + 1
    return counts


def week_label(days: list[dict[str, Any]]) -> str:
    first = parse_date(days[0]["date"])
    last = parse_date(days[-1]["date"])
    if first.month == last.month:
        return f"{first.day:02d} a {last.day:02d} {MONTH_NAMES[first.month]}"
    return f"{first.day:02d} {MONTH_NAMES[first.month]} a {last.day:02d} {MONTH_NAMES[last.month]}"


init_db()
seed_demo_data()


@app.context_processor
def inject_helpers() -> dict[str, Any]:
    return {
        "admin_logged_in": admin_logged_in(),
        "format_date_br": format_date_br,
        "format_full_date_br": format_full_date_br,
        "format_time_br": format_time_br,
        "weekday_name_from_date": weekday_name_from_date,
        "day_names": DAY_NAMES,
    }


@app.route("/")
def index():
    week_offset = request.args.get("week", default=0, type=int)
    days, viagens = build_week_instances(week_offset)
    selected_day = request.args.get("dia", days[0]["date"])
    counts = count_by_day(viagens)
    viagens_do_dia = [item for item in viagens if item["data_saida"] == selected_day]

    selected_day_label = format_full_date_br(selected_day)

    return render_template(
        "index.html",
        days=days,
        selected_day=selected_day,
        selected_day_label=selected_day_label,
        viagens_do_dia=viagens_do_dia,
        counts=counts,
        week_offset=week_offset,
        week_range_label=week_label(days),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if admin_logged_in():
        return redirect(url_for("admin"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        if usuario == ADMIN_USER and hashlib.sha256(senha.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session["admin_logado"] = True
            return redirect(url_for("admin"))

        flash("Usuario ou senha invalidos.", "erro")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    blocked = require_admin()
    if blocked is not None:
        return blocked

    rotas = list_rotas_semanais()

    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in request.form}
        required_fields = [
            "nome",
            "tipo",
            "origem",
            "destino",
            "dia_semana",
            "horario_saida",
            "horario_chegada",
            "telefone_contato",
        ]

        if any(not form.get(field) for field in required_fields):
            flash("Preencha todos os campos obrigatorios.", "erro")
            return render_template("admin.html", embarcacoes=rotas)

        try:
            capacidade = int(form.get("capacidade", "0"))
            dia_semana = int(form.get("dia_semana", "-1"))
            chegada_offset = int(form.get("chegada_dia_offset", "0"))
        except ValueError:
            capacidade = 0
            dia_semana = -1
            chegada_offset = 0

        if capacidade <= 0 or dia_semana not in DAY_NAMES or chegada_offset < 0:
            flash("Revise capacidade, dia da semana e chegada prevista.", "erro")
            return render_template("admin.html", embarcacoes=rotas)

        db = get_db()
        db.execute(
            """
            INSERT INTO viagens_semanais
            (nome, tipo, capacidade, origem, destino, dia_semana, horario_saida, horario_chegada,
             chegada_dia_offset, descricao, telefone_contato)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                form["nome"],
                form["tipo"],
                capacidade,
                form["origem"],
                form["destino"],
                dia_semana,
                form["horario_saida"],
                form["horario_chegada"],
                chegada_offset,
                form.get("descricao", ""),
                form["telefone_contato"],
            ),
        )
        db.commit()
        flash("Viagem semanal cadastrada com sucesso.", "sucesso")
        return redirect(url_for("admin"))

    return render_template("admin.html", embarcacoes=rotas)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
