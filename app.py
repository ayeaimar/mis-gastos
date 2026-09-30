import streamlit as st
import pandas as pd
import calendar

from datetime import date
from supabase import create_client


# ==================================================
# CONFIGURACIÓN GENERAL
# ==================================================

START_DATE = date(2026, 10, 1)

st.set_page_config(
    page_title="Mis Finanzas",
    page_icon="💰",
    layout="wide"
)


# ==================================================
# CONEXIÓN A SUPABASE
# ==================================================

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


# ==================================================
# FUNCIONES DE BASE DE DATOS
# ==================================================

def load_month_settings(month_key):
    try:
        response = (
            supabase
            .table("configuracion_mensual")
            .select("sueldo, objetivo_ahorro")
            .eq("mes", month_key)
            .execute()
        )

        if not response.data:
            return 1500000, 900000

        row = response.data[0]

        return (
            float(row["sueldo"]),
            float(row["objetivo_ahorro"])
        )

    except Exception as e:
        st.error(f"Error al cargar la configuración mensual: {e}")
        return 1500000, 900000


def save_month_settings(month_key, salary, savings_goal):
    try:
        supabase.table("configuracion_mensual").upsert(
            {
                "mes": month_key,
                "sueldo": float(salary),
                "objetivo_ahorro": float(savings_goal)
            },
            on_conflict="mes"
        ).execute()

    except Exception as e:
        st.error(f"Error al guardar la configuración mensual: {e}")


def load_expenses():
    try:
        response = (
            supabase
            .table("gastos")
            .select("id, categoria, descripcion, monto, fecha")
            .order("fecha", desc=True)
            .execute()
        )

        if not response.data:
            return pd.DataFrame(
                columns=[
                    "ID",
                    "Categoría",
                    "Descripción",
                    "Monto",
                    "Fecha"
                ]
            )

        df = pd.DataFrame(response.data)

        df = df.rename(
            columns={
                "id": "ID",
                "categoria": "Categoría",
                "descripcion": "Descripción",
                "monto": "Monto",
                "fecha": "Fecha"
            }
        )

        df["Monto"] = pd.to_numeric(
            df["Monto"],
            errors="coerce"
        ).fillna(0)

        return df

    except Exception as e:
        st.error(f"Error al cargar los gastos: {e}")

        return pd.DataFrame(
            columns=[
                "ID",
                "Categoría",
                "Descripción",
                "Monto",
                "Fecha"
            ]
        )


def save_expense(category, description, amount, expense_date):
    try:
        supabase.table("gastos").insert(
            {
                "categoria": category,
                "descripcion": description,
                "monto": float(amount),
                "fecha": expense_date.isoformat()
            }
        ).execute()

        return True

    except Exception as e:
        st.error(f"Error al guardar el gasto: {e}")
        return False


def delete_expense(expense_id):
    try:
        supabase.table("gastos").delete().eq(
            "id",
            int(expense_id)
        ).execute()

        return True

    except Exception as e:
        st.error(f"Error al eliminar el gasto: {e}")
        return False


def load_history():
    try:
        settings_response = (
            supabase
            .table("configuracion_mensual")
            .select("mes, sueldo, objetivo_ahorro")
            .execute()
        )

        expenses_response = (
            supabase
            .table("gastos")
            .select("fecha, monto")
            .execute()
        )

        # --------------------------
        # CONFIGURACIÓN
        # --------------------------

        if settings_response.data:

            settings = pd.DataFrame(
                settings_response.data
            )

            settings = settings.rename(
                columns={
                    "mes": "Mes",
                    "sueldo": "Sueldo",
                    "objetivo_ahorro": "Objetivo"
                }
            )

            settings["Sueldo"] = pd.to_numeric(
                settings["Sueldo"],
                errors="coerce"
            ).fillna(0)

            settings["Objetivo"] = pd.to_numeric(
                settings["Objetivo"],
                errors="coerce"
            ).fillna(0)

        else:

            settings = pd.DataFrame(
                columns=[
                    "Mes",
                    "Sueldo",
                    "Objetivo"
                ]
            )

        # --------------------------
        # GASTOS
        # --------------------------

        if expenses_response.data:

            expenses = pd.DataFrame(
                expenses_response.data
            )

            expenses["fecha"] = pd.to_datetime(
                expenses["fecha"],
                errors="coerce"
            )

            expenses["monto"] = pd.to_numeric(
                expenses["monto"],
                errors="coerce"
            ).fillna(0)

            expenses["Mes"] = (
                expenses["fecha"]
                .dt.to_period("M")
                .astype(str)
            )

            expenses = (
                expenses
                .groupby("Mes", as_index=False)["monto"]
                .sum()
            )

            expenses = expenses.rename(
                columns={
                    "monto": "Gastado"
                }
            )

        else:

            expenses = pd.DataFrame(
                columns=[
                    "Mes",
                    "Gastado"
                ]
            )

        # --------------------------
        # UNIR TODO
        # --------------------------

        history = settings.merge(
            expenses,
            on="Mes",
            how="outer"
        )

        for column in [
            "Sueldo",
            "Objetivo",
            "Gastado"
        ]:
            history[column] = (
                pd.to_numeric(
                    history[column],
                    errors="coerce"
                )
                .fillna(0)
            )

        history["Ahorro"] = (
            history["Sueldo"]
            - history["Gastado"]
        )

        return history.sort_values(
            "Mes",
            ascending=False
        )

    except Exception as e:

        st.error(
            f"Error al cargar el historial: {e}"
        )

        return pd.DataFrame()


# ==================================================
# ESTILOS
# ==================================================

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
    unsafe_allow_html=True
)


# ==================================================
# TÍTULO
# ==================================================

st.title("Mis Finanzas")

st.write(
    "Controlá tus gastos y cumplí tus objetivos de ahorro."
)

st.divider()


# ==================================================
# FECHA Y MES ACTUAL
# ==================================================

today = date.today()

active_date = max(
    today,
    START_DATE
)

month_names = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre"
]

current_month = (
    f"{month_names[active_date.month - 1].capitalize()} "
    f"{active_date.year}"
)

current_period = pd.Period(
    active_date,
    freq="M"
)

month_key = str(current_period)


# ==================================================
# CONFIGURACIÓN MENSUAL
# ==================================================

sueldo_inicial, objetivo_inicial = (
    load_month_settings(month_key)
)

st.subheader(
    f"Configuración de {current_month}"
)

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


# Guardamos solamente si cambió algo

if (
    sueldo != int(sueldo_inicial)
    or
    objetivo_ahorro != int(objetivo_inicial)
):

    save_month_settings(
        month_key,
        sueldo,
        objetivo_ahorro
    )


presupuesto_gastos = (
    sueldo
    - objetivo_ahorro
)


if presupuesto_gastos >= 0:

    st.info(
        f"Para ahorrar ${objetivo_ahorro:,.0f}, "
        f"podés gastar como máximo "
        f"${presupuesto_gastos:,.0f} durante "
        f"{current_month.lower()}."
    )

else:

    st.error(
        "El objetivo de ahorro es mayor que tu sueldo."
    )


st.divider()


# ==================================================
# CARGAR GASTOS
# ==================================================

st.subheader("Agregar gasto")

col1, col2, col3, col4 = st.columns(
    [1.1, 0.8, 1.4, 1]
)

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

    fecha = st.date_input(
        "Fecha",
        value=active_date,
        min_value=START_DATE
    )


if st.button(
    "Guardar gasto",
    use_container_width=True
):

    if monto > 0:

        guardado = save_expense(
            categoria,
            descripcion,
            monto,
            fecha
        )

        if guardado:

            st.success(
                "Gasto guardado correctamente."
            )

            st.rerun()

    else:

        st.warning(
            "Ingresá un monto mayor a $0."
        )


st.divider()


# ==================================================
# CARGAR Y FILTRAR GASTOS
# ==================================================

df_todos = load_expenses()

if not df_todos.empty:

    df_todos["Fecha"] = pd.to_datetime(
        df_todos["Fecha"],
        errors="coerce"
    )

    df_mes = df_todos[
        df_todos["Fecha"]
        .dt.to_period("M")
        == current_period
    ].copy()

else:

    df_mes = pd.DataFrame(
        columns=[
            "ID",
            "Categoría",
            "Descripción",
            "Monto",
            "Fecha"
        ]
    )


# ==================================================
# CÁLCULOS
# ==================================================

total_gastado = df_mes["Monto"].sum()

dinero_restante = (
    sueldo
    - total_gastado
)

ahorro_actual = (
    sueldo
    - total_gastado
)

presupuesto_restante = (
    presupuesto_gastos
    - total_gastado
)


# ==================================================
# DASHBOARD
# ==================================================

st.subheader(
    f"Resumen de {current_month}"
)

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


# ==================================================
# CONTROL DEL PRESUPUESTO
# ==================================================

st.subheader("Control de gastos")

if presupuesto_gastos > 0:

    porcentaje = (
        total_gastado
        / presupuesto_gastos
    )

    st.progress(
        min(
            float(porcentaje),
            1.0
        )
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
        "Llegaste exactamente al límite "
        "de gastos del mes."
    )

else:

    st.error(
        f"Superaste tu presupuesto de gastos por "
        f"${abs(presupuesto_restante):,.0f}."
    )


# ==================================================
# CALENDARIO
# ==================================================

st.divider()

st.subheader(
    f"Calendario de {current_month}"
)

if not df_mes.empty:

    gastos_diarios = (
        df_mes
        .assign(
            Día=df_mes["Fecha"].dt.day
        )
        .groupby("Día")["Monto"]
        .sum()
        .to_dict()
    )

else:

    gastos_diarios = {}


maximo_diario = max(
    gastos_diarios.values(),
    default=0
)

calendar_rows = []

calendar_rows.append(
    "".join(
        f"<div>{nombre}</div>"
        for nombre in [
            "Lun",
            "Mar",
            "Mié",
            "Jue",
            "Vie",
            "Sáb",
            "Dom"
        ]
    )
)


for week in calendar.monthcalendar(
    active_date.year,
    active_date.month
):

    for day_number in week:

        if day_number == 0:

            calendar_rows.append(
                '<div class="calendar-day empty"></div>'
            )

            continue

        gasto_diario = gastos_diarios.get(
            day_number,
            0
        )

        if (
            gasto_diario > 0
            and maximo_diario > 0
        ):

            intensity = (
                gasto_diario
                / maximo_diario
            )

            red = round(
                249 - (intensity * 65)
            )

            green = round(
                233 - (intensity * 145)
            )

            blue = round(
                231 - (intensity * 135)
            )

            background = (
                f"rgb({red}, {green}, {blue})"
            )

            foreground = (
                "#ffffff"
                if intensity > 0.58
                else "#5e3032"
            )

            amount = (
                f"${gasto_diario:,.0f}"
            )

        else:

            background = "#fafbf9"

            foreground = "#737a75"

            amount = "Sin gastos"

        calendar_rows.append(
            f'<div class="calendar-day" '
            f'style="background:{background}; '
            f'color:{foreground};">'
            f'<span class="calendar-day-number">'
            f'{day_number}'
            f'</span>'
            f'<span class="calendar-day-amount">'
            f'{amount}'
            f'</span>'
            f'</div>'
        )


st.markdown(
    '<div class="calendar">'
    '<div class="calendar-weekdays">'
    + calendar_rows[0]
    + '</div>'
    '<div class="calendar-grid">'
    + "".join(calendar_rows[1:])
    + '</div>'
    '<div class="calendar-legend">'
    '<span>Menor gasto</span>'
    '<span class="legend-swatch" '
    'style="background:#f9e9e7"></span>'
    '<span class="legend-swatch" '
    'style="background:#d97978"></span>'
    '<span class="legend-swatch" '
    'style="background:#b94a50"></span>'
    '<span>Mayor gasto</span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True
)


# ==================================================
# LISTA DE GASTOS
# ==================================================

st.divider()

st.subheader(
    f"Gastos de {current_month}"
)

if not df_mes.empty:

    tabla_gastos = (
        df_mes
        .sort_values(
            "Fecha",
            ascending=False
        )
        .copy()
    )

    tabla_gastos["Fecha"] = (
        tabla_gastos["Fecha"]
        .dt.strftime("%d/%m/%Y")
    )

    st.dataframe(
        tabla_gastos[
            [
                "Categoría",
                "Descripción",
                "Monto",
                "Fecha"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monto":
                st.column_config.NumberColumn(
                    "Monto",
                    format="$ %.0f"
                )
        }
    )


    # ----------------------------------------------
    # ELIMINAR GASTO
    # ----------------------------------------------

    with st.expander(
        "Eliminar un gasto"
    ):

        opciones = {}

        for _, row in (
            df_mes
            .sort_values(
                "Fecha",
                ascending=False
            )
            .iterrows()
        ):

            texto = (
                f"{row['Fecha'].strftime('%d/%m/%Y')} | "
                f"{row['Categoría']} | "
                f"{row['Descripción']} | "
                f"${row['Monto']:,.0f}"
            )

            opciones[texto] = row["ID"]

        gasto_seleccionado = st.selectbox(
            "Seleccioná el gasto",
            list(opciones.keys())
        )

        if st.button(
            "Eliminar gasto",
            type="secondary"
        ):

            if delete_expense(
                opciones[gasto_seleccionado]
            ):

                st.success(
                    "Gasto eliminado correctamente."
                )

                st.rerun()


    # ----------------------------------------------
    # GRÁFICO POR CATEGORÍA
    # ----------------------------------------------

    st.subheader(
        "Gastos por categoría"
    )

    gastos_categoria = (
        df_mes
        .groupby("Categoría")["Monto"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    st.bar_chart(
        gastos_categoria
    )

else:

    st.info(
        f"Todavía no cargaste gastos para "
        f"{current_month.lower()}."
    )


# ==================================================
# HISTORIAL MENSUAL
# ==================================================

st.divider()

st.subheader(
    "Historial mensual"
)

history = load_history()

if not history.empty:

    history["Mes"] = history["Mes"].map(
        lambda value:
            f"{month_names[int(value[5:7]) - 1].capitalize()} "
            f"{value[:4]}"
    )

    history = history.rename(
        columns={
            "Objetivo":
                "Objetivo de ahorro"
        }
    )

    st.dataframe(
        history[
            [
                "Mes",
                "Sueldo",
                "Gastado",
                "Ahorro",
                "Objetivo de ahorro"
            ]
        ].style.format(
            {
                "Sueldo":
                    "${:,.0f}",
                "Gastado":
                    "${:,.0f}",
                "Ahorro":
                    "${:,.0f}",
                "Objetivo de ahorro":
                    "${:,.0f}"
            }
        ),
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "El historial aparecerá cuando "
        "comience el seguimiento en octubre."
    )