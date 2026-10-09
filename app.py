# -*- coding: utf-8 -*-
"""
Mamíferos de Colombia - explorador taxonómico (versión 1)
Ejecutar desde Anaconda Prompt, dentro de la carpeta masto_web:
    streamlit run app.py
Necesita: mamiferos_imagenes.csv y la carpeta imagenes/ (salida de la Fase 2).
"""
import html
import random
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import ImageOps, Image

BASE = Path(__file__).parent
CSV = BASE / "mamiferos_final.csv"          # versión con nombres corregidos (Fase 3)
if not CSV.exists():
    CSV = BASE / "mamiferos_imagenes.csv"
IMG_DIR = BASE / "imagenes"
POR_PAGINA = 12

st.set_page_config(page_title="Mamíferos de Colombia", page_icon="🐾", layout="wide")


# ------------------------------------------------------------------ datos
CONECTORES = {"De", "Del", "La", "Las", "Los", "El", "Y", "Con", "En"}


def arreglar_mayusculas(s):
    """Primera letra en mayúscula y conectores (De, Del, La...) en minúscula."""
    if not s:
        return s
    p = [w.lower() if (i > 0 and w in CONECTORES) else w for i, w in enumerate(s.split(" "))]
    return " ".join(p)[:1].upper() + " ".join(p)[1:]


@st.cache_data
def cargar(version):          # 'version' cambia cuando el CSV cambia, así se refresca la caché
    df = pd.read_csv(CSV)
    texto = ["nombre_comun", "nombre_ingles", "imagen_archivo", "imagen_autor", "imagen_licencia",
             "imagen_fuente", "autoria", "cita", "id_fuente"]
    for c in texto:
        df[c] = df[c].fillna("").astype(str)
    df["nombre_comun"] = df["nombre_comun"].map(arreglar_mayusculas)
    df["titulo"] = df["nombre_comun"].where(df["nombre_comun"] != "", df["nombre_cientifico"])
    df["tiene_img"] = df["imagen_archivo"].map(lambda f: bool(f) and (IMG_DIR / f).exists())
    return df.sort_values(["orden", "familia", "genero", "epiteto"]).reset_index(drop=True)


df = cargar(CSV.stat().st_mtime)
por_sci = df.set_index("nombre_cientifico")


@st.cache_data(show_spinner=False)
def imagen_cuadrada(ruta, lado=500):
    """Recorta la foto a un cuadrado para que todas las tarjetas queden del mismo tamaño."""
    with Image.open(ruta) as im:
        return ImageOps.fit(im.convert("RGB"), (lado, lado))


def bloque_cuadrado(texto, fondo="#EAF0EA", color="#6B7A70", tam="1.3rem"):
    st.markdown(f"<div style='aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;"
                f"background:{fondo};color:{color};border-radius:8px;padding:1rem;text-align:center;margin-bottom:1rem;"
                f"font-size:{tam};font-weight:600'>{html.escape(texto)}</div>", unsafe_allow_html=True)


def mostrar_imagen(fila, cuadrada=False):
    if fila["tiene_img"]:
        ruta = str(IMG_DIR / fila["imagen_archivo"])
        st.image(imagen_cuadrada(ruta) if cuadrada else ruta)
    elif cuadrada:
        bloque_cuadrado("Sin imagen", tam="1rem")
    else:
        st.markdown("<div style='background:#EAF0EA;color:#6B7A70;padding:3.2rem 0;text-align:center;"
                    "border-radius:8px'>Sin imagen</div>", unsafe_allow_html=True)


def ir_ficha(sci):
    st.session_state["sel"] = sci
    st.session_state["pagina"] = "Ficha de especie"


# ------------------------------------------------------------------ páginas
def pagina_arbol():
    st.header("Árbol taxonómico")
    st.caption("Clase Mammalia → Orden → Familia → Especie. Haz clic en un sector del gráfico para "
               "entrar a ese grupo, y en el centro para volver.")
    fig = px.sunburst(df, path=["orden", "familia", "nombre_cientifico"], maxdepth=2,
                      color="orden", color_discrete_sequence=px.colors.qualitative.Safe)
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=620, showlegend=False)
    st.plotly_chart(fig)

    st.subheader("Lista por orden")
    for orden, g in df.groupby("orden"):
        with st.expander(f"{orden}  ·  {len(g)} especies  ·  {g['familia'].nunique()} familias"):
            for fam, gf in g.groupby("familia"):
                especies = ", ".join(f"*{s}*" for s in gf["nombre_cientifico"])
                st.markdown(f"**{fam}** ({len(gf)}): {especies}")


def pagina_explorar():
    st.header("Explorar especies")
    c1, c2, c3 = st.columns([1, 1, 2])
    orden = c1.selectbox("Orden", ["Todos"] + sorted(df["orden"].unique()))
    base = df if orden == "Todos" else df[df["orden"] == orden]
    familia = c2.selectbox("Familia", ["Todas"] + sorted(base["familia"].unique()))
    if familia != "Todas":
        base = base[base["familia"] == familia]
    q = c3.text_input("Buscar por nombre", placeholder="jaguar, Panthera, manatí...").strip().lower()
    if q:
        m = (base["nombre_cientifico"].str.lower().str.contains(q) |
             base["nombre_comun"].str.lower().str.contains(q) |
             base["nombre_ingles"].str.lower().str.contains(q))
        base = base[m]
    solo_img = st.checkbox("Solo especies con imagen")
    if solo_img:
        base = base[base["tiene_img"]]

    total = len(base)
    paginas = max(1, -(-total // POR_PAGINA))
    pag = st.number_input(f"Página (de {paginas})", min_value=1, max_value=paginas, value=1, step=1)
    st.write(f"**{total}** especies")
    sub = base.iloc[(pag - 1) * POR_PAGINA: pag * POR_PAGINA]
    for ini in range(0, len(sub), 4):                      # una fila de 4 tarjetas a la vez
        cols = st.columns(4)
        for col, (_, f) in zip(cols, sub.iloc[ini:ini + 4].iterrows()):
            with col:
                mostrar_imagen(f, cuadrada=True)
                if f["nombre_comun"]:
                    st.markdown(f"**{f['nombre_comun']}**")
                    st.caption(f"*{f['nombre_cientifico']}* · {f['familia']}")
                else:                                   # sin nombre común: el científico es el título
                    st.markdown(f"***{f['nombre_cientifico']}***")
                    st.caption(f["familia"])
                st.button("Ver ficha", key=f"v_{f['nombre_cientifico']}", on_click=ir_ficha,
                          args=(f["nombre_cientifico"],))


def pagina_ficha():
    st.header("Ficha de especie")
    opciones = list(df["nombre_cientifico"])
    if "sel" not in st.session_state:
        st.session_state["sel"] = opciones[0]
    sci = st.selectbox("Especie", opciones, key="sel",
                       format_func=lambda s: f"{por_sci.loc[s, 'titulo']}  ({s})"
                       if por_sci.loc[s, "nombre_comun"] else s)
    f = por_sci.loc[sci].copy()
    f["nombre_cientifico"] = sci
    c1, c2 = st.columns([1, 1.2])
    with c1:
        mostrar_imagen(f)
        if f["tiene_img"]:
            st.caption(f"Foto: {f['imagen_autor']} · licencia {f['imagen_licencia'].upper()} · "
                       f"[fuente]({f['imagen_fuente']})")
    with c2:
        st.subheader(f["titulo"])
        st.markdown(f"*{sci}* {f['autoria']}")
        if f["nombre_ingles"]:
            st.write(f"**Inglés:** {f['nombre_ingles']}")
        st.markdown(f"**Clasificación:** Mammalia › {f['orden']} › {f['familia']} › "
                    f"*{f['genero']}* › *{sci}*")
        if pd.notna(f["elevacion_min_m"]):
            st.write(f"**Rango altitudinal:** {int(f['elevacion_min_m'])} – {int(f['elevacion_max_m'])} m")
        else:
            st.write("**Rango altitudinal:** sin dato")
        q = sci.replace(" ", "+")
        enlaces = [f"[GBIF](https://www.gbif.org/species/search?q={q})",
                   f"[Wikipedia](https://es.wikipedia.org/w/index.php?search={q})"]
        if pd.notna(f["inat_id"]):
            enlaces.append(f"[iNaturalist](https://www.inaturalist.org/taxa/{int(f['inat_id'])})")
        st.markdown("**Más información:** " + " · ".join(enlaces))
        st.caption(f"Referencia: {f['cita']}")


def pagina_aprender():
    st.header("Aprender taxonomía")
    st.write("Cada especie se clasifica en rangos anidados, del más general al más específico. "
             "Elige una especie para ver su ruta completa.")
    sci = st.selectbox("Especie de ejemplo", list(df["nombre_cientifico"]),
                       format_func=lambda s: f"{por_sci.loc[s, 'titulo']}  ({s})")
    f = por_sci.loc[sci]
    tabla = pd.DataFrame({
        "Rango": ["Reino", "Filo", "Clase", "Orden", "Familia", "Género", "Especie"],
        "Taxón": ["Animalia", "Chordata", "Mammalia", f["orden"], f["familia"], f["genero"], sci]})
    st.table(tabla.set_index("Rango"))
    st.subheader("Datos del conjunto")
    a, b, c, d = st.columns(4)
    a.metric("Especies", len(df)); b.metric("Órdenes", df["orden"].nunique())
    c.metric("Familias", df["familia"].nunique()); d.metric("Géneros", df["genero"].nunique())
    st.bar_chart(df["orden"].value_counts())


def nuevo_juego(modo, n):
    d = df[df["tiene_img"]]
    if modo in ("Familia", "Orden"):               # evita pares ambiguos
        d = d.drop_duplicates(modo.lower())
    muestra = d.sample(min(n, len(d)))
    cartas = []
    for sci in muestra["nombre_cientifico"]:
        cartas += [{"par": sci, "tipo": "img"}, {"par": sci, "tipo": "txt"}]
    random.shuffle(cartas)
    st.session_state["juego"] = {"cartas": cartas, "modo": modo, "vistas": [], "ok": set(), "movs": 0}


def voltear(i):
    j = st.session_state["juego"]
    if len(j["vistas"]) == 2:
        j["vistas"] = []
    j["vistas"].append(i)
    if len(j["vistas"]) == 2:
        j["movs"] += 1
        a, b = j["vistas"]
        if j["cartas"][a]["par"] == j["cartas"][b]["par"]:
            j["ok"].add(j["cartas"][a]["par"])
            j["vistas"] = []


def texto_carta(sci, modo):
    f = por_sci.loc[sci]
    return {"Nombre común": f["titulo"], "Nombre científico": sci,
            "Familia": f["familia"], "Orden": f["orden"]}[modo]


def pagina_juego():
    st.header("Juego de memoria")
    st.write("Une cada foto con su tarjeta de texto.")
    c1, c2, c3 = st.columns([1.3, 1, 1])
    modo = c1.selectbox("La tarjeta de texto muestra", ["Nombre común", "Nombre científico", "Familia", "Orden"])
    n = c2.selectbox("Pares", [4, 6, 8], index=1)
    c3.write("")
    if c3.button("Nueva partida") or "juego" not in st.session_state:
        nuevo_juego(modo, n)
    j = st.session_state["juego"]
    st.write(f"Movimientos: **{j['movs']}**  ·  Pares encontrados: **{len(j['ok'])}/{len(j['cartas']) // 2}**")
    total = len(j["cartas"])
    for ini in range(0, total, 4):                         # una fila de 4 cartas a la vez
        cols = st.columns(4)
        for k, col in enumerate(cols):
            i = ini + k
            if i >= total:
                break
            carta = j["cartas"][i]
            with col:
                if carta["par"] in j["ok"] or i in j["vistas"]:
                    if carta["tipo"] == "img":
                        mostrar_imagen(por_sci.loc[carta["par"]].to_dict(), cuadrada=True)
                    else:
                        bloque_cuadrado(texto_carta(carta["par"], j["modo"]), color="#1E2A24")
                    if carta["par"] in j["ok"]:
                        st.caption("✓ pareja")
                else:
                    st.button("❓", key=f"c{i}", on_click=voltear, args=(i,))
    if len(j["ok"]) == len(j["cartas"]) // 2:
        st.balloons()
        st.success(f"¡Completado en {j['movs']} movimientos!")


def pagina_creditos():
    st.header("Créditos de las imágenes")
    st.write("Todas las fotos provienen de iNaturalist y se usan bajo la licencia indicada por su autor. "
             "Las licencias *NC* (no comercial) permiten uso educativo sin fines de lucro.")
    t = df.loc[df["tiene_img"], ["nombre_cientifico", "imagen_autor", "imagen_licencia", "imagen_fuente"]]
    st.dataframe(t, hide_index=True,
                 column_config={"imagen_fuente": st.column_config.LinkColumn("Fuente"),
                                "nombre_cientifico": "Especie", "imagen_autor": "Autor",
                                "imagen_licencia": "Licencia"})


# ------------------------------------------------------------------ navegación
PAGINAS = {"Árbol taxonómico": pagina_arbol, "Explorar": pagina_explorar,
           "Ficha de especie": pagina_ficha, "Aprender": pagina_aprender,
           "Juego de memoria": pagina_juego, "Créditos": pagina_creditos}

st.sidebar.title("🐾 Mamíferos de Colombia")
st.sidebar.radio("Sección", list(PAGINAS), key="pagina")
st.sidebar.caption(f"{len(df)} especies · {int(df['tiene_img'].sum())} con imagen")
PAGINAS[st.session_state["pagina"]]()
