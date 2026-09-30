import streamlit as st
import pandas as pd
import calendar
import sqlite3
from datetime import date
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("finanzas.db")
START_DATE = date(2026, 10, 1)


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                monto REAL NOT NULL,
                fecha TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracion_mensual (
                mes TEXT PRIMARY KEY,
                sueldo REAL NOT NULL,
                objetivo_ahorro REAL NOT NULL
            )
            """
        )


def load_month_settings(month_key):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT sueldo, objetivo_ahorro FROM configuracion_mensual WHERE mes = ?",
            (month_key,),
        ).fetchone()

    if row is None:
        return 1500000, 900000

    return row["sueldo"], row["objetivo_ahorro"]


def save_month_settings(month_key, salary, savings_goal):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO configuracion_mensual (mes, sueldo, objetivo_ahorro)
            VALUES (?, ?, ?)
            ON CONFLICT(mes) DO UPDATE SET
                sueldo = excluded.sueldo,
                objetivo_ahorro = excluded.objetivo_ahorro
            """,
            (month_key, salary, savings_goal),
        )


def load_expenses():
    with get_connection() as connection:
        return pd.read_sql_query(
            """
            SELECT
                categoria AS Categoría,
                descripcion AS Descripción,
                monto AS Monto,
                fecha AS Fecha
            FROM gastos
            ORDER BY fecha DESC, id DESC
            """,
            connection,
        )


def save_expense(category, description, amount, expense_date):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO gastos (categoria, descripcion, monto, fecha)
            VALUES (?, ?, ?, ?)
            """,
            (category, description, amount, expense_date.isoformat()),
        )


def load_history():
    with get_connection() as connection:
        settings = pd.read_sql_query(
            """
            SELECT mes AS Mes, sueldo AS Sueldo, objetivo_ahorro AS Objetivo
            FROM configuracion_mensual
            """,
            connection,
        )
        expenses = pd.read_sql_query(
            """
            SELECT strftime('%Y-%m', fecha) AS Mes, SUM(monto) AS Gastado
            FROM gastos
            GROUP BY strftime('%Y-%m', fecha)
            """,
            connection,
        )

    history = settings.merge(expenses, on="Mes", how="outer")
    for column in ["Sueldo", "Objetivo", "Gastado"]:
        history[column] = history[column].fillna(0)
    history["Ahorro"] = history["Sueldo"] - history["Gastado"]
    return history.sort_values("Mes", ascending=False)


initialize_database()

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="Mis Finanzas",
    layout="wide"
)

st.markdown(
    """
    <style>
        :root {
            --ink: #3f4542;
            --muted: #737a75;
            --line: #dfe3dd;
            --surface: #ffffff;
            --sage: #dce8df;
            --sage-strong: #789782;
            --blush: #f1e2df;
            --sand: #f3eee5;
        }

        .stApp {
            background: #f7f8f5;
            color: var(--ink);
        }

        ::selection {
            background: #cbded0;
            color: var(--ink);
        }

        [data-testid="stHeader"] {
            background: rgba(247, 248, 245, 0.88);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        h1 {
            font-size: 2.8rem !important;
            font-weight: 700 !important;
        }

        h2, h3 {
            font-weight: 650 !important;
        }

        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: 0 5px 18px rgba(73, 82, 74, 0.05);
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
        }

        [data-testid="stMetricValue"] {
            color: var(--ink);
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea,
        input {
            background: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #9aa19c !important;
            -webkit-text-fill-color: #9aa19c !important;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        [data-baseweb="select"] span,
        [data-baseweb="select"] div,
        [data-baseweb="input"] button,
        [data-testid="stDateInput"] button {
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
        }

        [data-testid="stDateInput"] input {
            background: var(--surface) !important;
            color: var(--ink) !important;
            -webkit-text-fill-color: var(--ink) !important;
        }

        .stButton > button {
            background: var(--sage-strong);
            color: white;
            border: 0;
            border-radius: 8px;
            min-height: 2.7rem;
            font-weight: 600;
        }

        .stButton > button:hover {
            background: #668572;
            color: white;
        }

        [data-testid="stAlert"] {
            border: 1px solid var(--line);
            border-radius: 10px;
        }

        hr {
            border-color: var(--line);
        }

        .calendar {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 5px 18px rgba(73, 82, 74, 0.05);
        }

        .calendar-weekdays,
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 0.45rem;
        }

        .calendar-weekdays {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 650;
            padding: 0 0.25rem 0.5rem;
            text-align: center;
        }

        .calendar-day {
            aspect-ratio: 1.15;
            border: 1px solid var(--line);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 4.4rem;
            padding: 0.55rem;
        }

        .calendar-day.empty {
            background: #fafbf9;
            border-color: transparent;
        }

        .calendar-day-number {
            font-size: 0.85rem;
            font-weight: 650;
        }

        .calendar-day-amount {
            font-size: 0.72rem;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }

        .calendar-legend {
            align-items: center;
            color: var(--muted);
            display: flex;
            font-size: 0.8rem;
            gap: 0.45rem;
            justify-content: flex-end;
            margin-top: 0.8rem;
        }

        .legend-swatch {
            border-radius: 4px;
            height: 0.8rem;
            width: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# TÍTULO
# --------------------------------------------------

st.title("Mis Finanzas")
st.write("Controlá tus gastos y cumplí tus objetivos de ahorro.")

st.divider()

# --------------------------------------------------
# CONFIGURACIÓN MENSUAL
# --------------------------------------------------

today = date.today()
active_date = max(today, START_DATE)
month_names = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]
current_month = f"{month_names[active_date.month - 1].capitalize()} {active_date.year}"
current_period = pd.Period(active_date, freq="M")
month_key = str(current_period)
sueldo_inicial, objetivo_inicial = load_month_settings(month_key)

st.subheader(f"Configuración de {current_month}")

col1, col2 = st.columns(2)

with col1:
    sueldo = st.number_input(
        "Sueldo mensual",
        min_value=0,
        value=int(sueldo_inicial),
        step=50000
    )

with col2:
    objetivo_ahorro = st.number_input(
        "¿Cuánto querés ahorrar este mes?",
        min_value=0,
        value=int(objetivo_inicial),
        step=50000
    )

    save_month_settings(month_key, sueldo, objetivo_ahorro)

presupuesto_gastos = sueldo - objetivo_ahorro

st.info(
    f"Para ahorrar ${objetivo_ahorro:,.0f}, "
    f"podés gastar como máximo ${presupuesto_gastos:,.0f} durante {current_month.lower()}."
)

st.divider()

# --------------------------------------------------
# CARGAR GASTOS
# --------------------------------------------------

st.subheader("Agregar gasto")

col1, col2, col3, col4 = st.columns([1.1, 0.8, 1.4, 1])

with col1:
    categoria = st.selectbox(
        "Categoría",
        [
            "Comida",
            "Transporte",
            "Vivienda",
            "Salidas",
            "Ropa",
            "Deporte",
            "Salud",
            "Educación",
            "Suscripciones",
            "Regalos",
            "Otros"
        ]
    )

with col2:
    monto = st.number_input(
        "Monto",
        min_value=0,
        step=1000
    )

with col3:
    descripcion = st.text_input(
        "Descripción",
        placeholder="Ej: Supermercado"
    )

with col4:
    fecha = st.date_input("Fecha", value=active_date, min_value=START_DATE)

if st.button("Guardar gasto", use_container_width=True):

    if monto > 0:

        save_expense(categoria, descripcion, monto, fecha)

        st.success("Gasto guardado correctamente.")

    else:
        st.warning("Ingresá un monto mayor a $0.")

st.divider()

# --------------------------------------------------
# CALCULOS
# --------------------------------------------------

df_todos = load_expenses()

if not df_todos.empty:
    fecha_registros = df_todos.get("Fecha", pd.Series(pd.NaT, index=df_todos.index))
    df_todos["Fecha"] = pd.to_datetime(fecha_registros, errors="coerce")
    df_mes = df_todos[df_todos["Fecha"].dt.to_period("M") == current_period].copy()
else:
    df_mes = pd.DataFrame(columns=["Categoría", "Descripción", "Monto", "Fecha"])

total_gastado = df_mes["Monto"].sum()

dinero_restante = sueldo - total_gastado

ahorro_actual = sueldo - total_gastado

presupuesto_restante = presupuesto_gastos - total_gastado

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

st.subheader(f"Resumen de {current_month}")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Sueldo",
    f"${sueldo:,.0f}"
)

col2.metric(
    "Gastado",
    f"${total_gastado:,.0f}"
)

col3.metric(
    "Dinero restante",
    f"${dinero_restante:,.0f}"
)

col4.metric(
    "Objetivo de ahorro",
    f"${objetivo_ahorro:,.0f}"
)

# --------------------------------------------------
# CONTROL DEL PRESUPUESTO
# --------------------------------------------------

st.subheader("Control de gastos")

if presupuesto_gastos > 0:

    porcentaje = total_gastado / presupuesto_gastos

    st.progress(
        min(porcentaje, 1.0)
    )

    st.write(
        f"Usaste **{porcentaje * 100:.1f}%** "
        f"de tu presupuesto para gastos."
    )

if presupuesto_restante > 0:

    st.success(
        f"Todavía podés gastar "
        f"${presupuesto_restante:,.0f} "
        f"y cumplir tu objetivo de ahorro."
    )

elif presupuesto_restante == 0:

    st.warning(
        "Llegaste exactamente al límite de gastos del mes."
    )

else:

    st.error(
        f"Superaste tu presupuesto de gastos por "
        f"${abs(presupuesto_restante):,.0f}."
    )

# --------------------------------------------------
# CALENDARIO MENSUAL
# --------------------------------------------------

st.divider()
st.subheader(f"Calendario de {current_month}")

if not df_mes.empty:
    gastos_diarios = (
        df_mes.assign(Día=df_mes["Fecha"].dt.day)
        .groupby("Día")["Monto"]
        .sum()
        .to_dict()
    )
else:
    gastos_diarios = {}

maximo_diario = max(gastos_diarios.values(), default=0)
calendar_rows = []
calendar_rows.append(
    "".join(
        f'<div>{nombre}</div>'
        for nombre in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    )
)

for week in calendar.monthcalendar(active_date.year, active_date.month):
    for day_number in week:
        if day_number == 0:
            calendar_rows.append('<div class="calendar-day empty"></div>')
            continue

        gasto_diario = gastos_diarios.get(day_number, 0)
        if gasto_diario > 0 and maximo_diario > 0:
            intensity = gasto_diario / maximo_diario
            red = round(249 - (intensity * 65))
            green = round(233 - (intensity * 145))
            blue = round(231 - (intensity * 135))
            background = f"rgb({red}, {green}, {blue})"
            foreground = "#ffffff" if intensity > 0.58 else "#5e3032"
            amount = f"${gasto_diario:,.0f}"
        else:
            background = "#fafbf9"
            foreground = "#737a75"
            amount = "Sin gastos"

        calendar_rows.append(
            f'<div class="calendar-day" style="background:{background}; color:{foreground};">'
            f'<span class="calendar-day-number">{day_number}</span>'
            f'<span class="calendar-day-amount">{amount}</span>'
            "</div>"
        )

st.markdown(
    '<div class="calendar">'
    '<div class="calendar-weekdays">'
    + calendar_rows[0]
    + '</div><div class="calendar-grid">'
    + "".join(calendar_rows[1:])
    + '</div><div class="calendar-legend">'
    '<span>Menor gasto</span>'
    '<span class="legend-swatch" style="background:#f9e9e7"></span>'
    '<span class="legend-swatch" style="background:#d97978"></span>'
    '<span class="legend-swatch" style="background:#b94a50"></span>'
    '<span>Mayor gasto</span>'
    '</div></div>',
    unsafe_allow_html=True,
)

# --------------------------------------------------
# LISTA DE GASTOS
# --------------------------------------------------

st.divider()

st.subheader(f"Gastos de {current_month}")

if not df_mes.empty:

    st.dataframe(
        df_mes.sort_values("Fecha", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # Gastos por categoría

    st.subheader("Gastos por categoría")

    gastos_categoria = (
        df_mes.groupby("Categoría")["Monto"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(gastos_categoria)

else:

    st.info(f"Todavía no cargaste gastos para {current_month.lower()}.")

# --------------------------------------------------
# HISTORIAL MENSUAL
# --------------------------------------------------

st.divider()
st.subheader("Historial mensual")

history = load_history()

if not history.empty:
    history["Mes"] = history["Mes"].map(
        lambda value: f"{month_names[int(value[5:7]) - 1].capitalize()} {value[:4]}"
    )
    history = history.rename(
        columns={
            "Sueldo": "Sueldo",
            "Gastado": "Gastado",
            "Ahorro": "Ahorro",
            "Objetivo": "Objetivo de ahorro",
        }
    )
    st.dataframe(
        history[["Mes", "Sueldo", "Gastado", "Ahorro", "Objetivo de ahorro"]]
        .style.format(
            {
                "Sueldo": "${:,.0f}",
                "Gastado": "${:,.0f}",
                "Ahorro": "${:,.0f}",
                "Objetivo de ahorro": "${:,.0f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("El historial aparecerá cuando comience el seguimiento en octubre.")