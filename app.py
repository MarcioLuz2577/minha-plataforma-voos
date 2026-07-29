# -*- coding: utf-8 -*-
"""
Caçador Particular de Passagens & Milhas
========================================
Busca em tempo real no Google Flights (SerpApi) com duas estratégias:
  A) Trechos separados (ida + volta independentes) -> captura cias/rotas isoladas
  B) Ida e volta unificada (round-trip unico)        -> captura tarifas como LATAM que saem mais baratas juntas

Resultado normalizado em estrutura unica (Passo 3).
Framework de recomendacao cash vs milhas (Passo 5) - pronto para integracao de API de milhas (Passo 6).
"""

import datetime
from serpapi import GoogleSearch
import streamlit as st


# ============================================================
# CONFIGURACAO DA PAGINA
# ============================================================
st.set_page_config(
    page_title="Cacador de Passagens - Multi-Estrategia",
    page_icon=":airplane:",
    layout="wide",
)

st.title(":airplane: Cacador Particular de Passagens & Milhas")
st.caption(
    "Busca em tempo real no Google Flights (SerpApi) - "
    "Estrategia A: trechos separados | Estrategia B: ida e volta unificada"
)


# ============================================================
# SECRETS
# ============================================================
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")


# ============================================================
# DICIONARIO DE AEROPORTOS
# ============================================================
AEROPORTOS = {
    "Sao Paulo - Todos os Aeroportos (SAO)": "SAO",
    "Sao Paulo - Guarulhos (GRU)": "GRU",
    "Sao Paulo - Congonhas (CGH)": "CGH",
    "Sao Paulo - Viracopos / Campinas (VCP)": "VCP",
    "Rio de Janeiro - Todos os Aeroportos (RIO)": "RIO",
    "Rio de Janeiro - Galeao (GIG)": "GIG",
    "Rio de Janeiro - Santos Dumont (SDU)": "SDU",
    "Belo Horizonte - Confins (CNF)": "CNF",
    "Belo Horizonte - Pampulha (PLU)": "PLU",
    "Brasilia (BSB)": "BSB",
    "Salvador (SSA)": "SSA",
    "Recife (REC)": "REC",
    "Fortaleza (FOR)": "FOR",
    "Passo Fundo (POA)": "POA",
    "Curitiba (CWB)": "CWB",
    "Florianopolis (FLN)": "FLN",
    "Manaus (MAO)": "MAO",
    "Belem (BEL)": "BEL",
    "Goiania (GYN)": "GYN",
    "Vitoria (VIX)": "VIX",
    "Mendoza (MDZ)": "MDZ",
    "Buenos Aires - Todos (BUE)": "BUE",
    "Miami (MIA)": "MIA",
    "Orlando (MCO)": "MCO",
    "Nova York - Todos (NYC)": "NYC",
    "Lisboa (LIS)": "LIS",
    "Madri (MAD)": "MAD",
}

lista_opcoes_aeroportos = list(AEROPORTOS.keys())


# ============================================================
# OPCOES SUPERIORES DE FILTRO
# ============================================================
col_opt1, col_opt2 = st.columns(2)

with col_opt1:
    tipo_viagem = st.radio(
        "Tipo de Viagem:",
        options=["Somente Ida", "Ida e Volta"],
        horizontal=True,
        index=0,
    )

with col_opt2:
    classe_cabine = st.radio(
        "Classe:",
        options=["economy", "business", "first"],
        horizontal=True,
        index=0,
        format_func=lambda x: {"economy": "Economica", "business": "Executiva", "first": "Primeira Classe"}[x],
    )

st.write("")


# ============================================================
# FORMULARIO DE BUSCA
# ============================================================
col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
    origem_sel = st.selectbox(":airplane: Origem", options=lista_opcoes_aeroportos, index=1)
    origem_iata = AEROPORTOS[origem_sel]

with col2:
    destino_sel = st.selectbox(":airplane: Destino", options=lista_opcoes_aeroportos, index=5)
    destino_iata = AEROPORTOS[destino_sel]

with col3:
    data_ida = st.date_input("Data de Ida", datetime.date.today() + datetime.timedelta(days=7))

with col4:
    if tipo_viagem == "Ida e Volta":
        data_volta = st.date_input("Data de Volta", data_ida + datetime.timedelta(days=7))
    else:
        data_volta = None
        st.text_input("Data de Volta", value="Apenas Ida", disabled=True)

with col5:
    num_pax = st.number_input("Passageiros", min_value=1, max_value=9, value=1)


# ============================================================
# PASSO 3: NORMALIZACAO EM ESTRUTURA UNICA
# ============================================================
def formatar_duracao(minutos):
    if not minutos:
        return "N/A"
    return f"{minutos // 60}h {minutos % 60}m"

def normalizar_oferta_serp(flight_option, trecho, estrategia, indice):
    """
    Transforma uma oferta bruta do Google Flights em um dicionario padronizado,
    independente da estrategia de busca (A ou B) ou do trecho (ida/volta/ida_volta).

    Retorna None se a oferta estiver vazia.
    """
    flights = flight_option.get("flights", [])
    if not flights:
        return None

    primeiro = flights[0]
    ultimo = flights[-1]

    cia_primeiro = primeiro.get("airline", "")
    cia_ultimo = ultimo.get("airline", "")
    if cia_primeiro and cia_ultimo and cia_primeiro != cia_ultimo:
        cia = f"{cia_primeiro} / {cia_ultimo}"
    else:
        cia = cia_primeiro or cia_ultimo or "Companhia Aerea"

    num_primeiro = primeiro.get("flight_number", "")
    num_ultimo = ultimo.get("flight_number", "")
    nums = [n for n in [num_primeiro, num_ultimo] if n]
    num_voo = " / ".join(nums) if nums else ""

    dep_airport = flights[0].get("departure_airport", {})
    arr_airport = flights[-1].get("arrival_airport", {})
    dep_time = (dep_airport.get("time", "") or "").split()[-1]
    arr_time = (arr_airport.get("time", "") or "").split()[-1]

    escalas = max(0, len(flights) - 1)

    duracao_min = flight_option.get("total_duration", 0)
    preco = flight_option.get("price", 0)
    moeda = flight_option.get("currency", "BRL")
    tipo_token = flight_option.get("type", "")  # best_flights / other_flights

    return {
        # identidade da oferta
        "fonte": "Google Flights",
        "estrategia": estrategia,   # "A_separado" ou "B_unificado"
        "trecho": trecho,           # "ida", "volta" ou "ida_volta"
        "indice": indice,
        "tipo_token": "Melhor" if tipo_token == "best_flights" else "Outra",

        # informacoes do voo
        "cia": cia,
        "num_voo": num_voo,
        "escalas": escalas,
        "duracao_min": duracao_min,
        "duracao_fmt": formatar_duracao(duracao_min),

        # aeroportos/horarios
        "dep_iata": dep_airport.get("id", ""),
        "dep_time": dep_time,
        "arr_iata": arr_airport.get("id", ""),
        "arr_time": arr_time,

        # preco
        "preco": float(preco) if preco is not None else 0.0,
        "moeda": moeda,
    }


# ============================================================
# BUSCAS SERPAPI
# ============================================================
def _executar_serpapi(params, label_erro):
    try:
        results = GoogleSearch(params).get_dict()
        todas = []
        if "best_flights" in results:
            todas.extend(results["best_flights"])
        if "other_flights" in results:
            todas.extend(results["other_flights"])
        return todas
    except Exception as e:
        st.warning(f"Aviso SerpApi ({label_erro}): {e}")
        return []

def buscar_serpapi_oneway(dep_iata, arr_iata, data_obj, adultos, classe):
    """Estrategia A: busca um trecho so (one-way, type=2)."""
    if not SERPAPI_KEY:
        return []
    params = {
        "engine": "google_flights",
        "departure_id": dep_iata,
        "arrival_id": arr_iata,
        "outbound_date": data_obj.strftime("%Y-%m-%d"),
        "currency": "BRL",
        "hl": "pt",
        "gl": "br",
        "type": "2",
        "adults": int(adultos),
        "travel_class": classe,
        "api_key": SERPAPI_KEY,
    }
    return _executar_serpapi(params, f"one-way {dep_iata}-{arr_iata}")

def buscar_serpapi_roundtrip(dep_iata, arr_iata, data_ida_obj, data_volta_obj, adultos, classe):
    """Estrategia B: busca ida e volta unificada (round-trip, type=1)."""
    if not SERPAPI_KEY:
        return []
    params = {
        "engine": "google_flights",
        "departure_id": dep_iata,
        "arrival_id": arr_iata,
        "outbound_date": data_ida_obj.strftime("%Y-%m-%d"),
        "return_date": data_volta_obj.strftime("%Y-%m-%d"),
        "currency": "BRL",
        "hl": "pt",
        "gl": "br",
        "type": "1",
        "adults": int(adultos),
        "travel_class": classe,
        "api_key": SERPAPI_KEY,
    }
    return _executar_serpapi(params, f"round-trip {dep_iata}-{arr_iata}")


# ============================================================
# PASSO 5: RECOMENDACAO (FRAMEWORK - AGUARDANDO PASSO 6)
# ============================================================
# Os tres estados de recomendacao do produto. A logica decisoria sera
# conectada quando o Passo 6 (API de milhas) estiver integrado.
ESTADOS_RECOMENDACAO = {
    "milhas": {
        "emoji": ":sparkles:",
        "rotulo": "VALE EMITIR COM MILHAS",
        "cor": "success",
        "explicacao": (
            "A emissao em milhas oferece o melhor custo-beneficio para esta rota. "
            "Verifique a disponibilidade de assentos no programa indicado."
        ),
    },
    "dinheiro": {
        "emoji": ":money_with_wings:",
        "rotulo": "MELHOR PAGAR EM DINHEIRO",
        "cor": "warning",
        "explicacao": (
            "O valor da milha nesta rota esta baixo. "
            "Pagar em dinheiro preserva seus pontos para oportunidades melhores."
        ),
    },
    "aguardar": {
        "emoji": ":hourglass:",
        "rotulo": "AGUARDAR TRANSFERENCIA BONIFICADA OU ALERTA DE DISPONIBILIDADE",
        "cor": "info",
        "explicacao": (
            "Nenhum dos lados esta claramente vantajoso agora. "
            "Recomendado aguardar bonus de transferencia de pontos ou alerta de "
            "disponibilidade de assentos em classe premium."
        ),
    },
}

def exibir_recomendacao(estado, detalhe_extra=None):
    """Exibe o card de recomendacao na UI. Logica decisoria sera ligada no Passo 6."""
    cfg = ESTADOS_RECOMENDACAO.get(estado, ESTADOS_RECOMENDACAO["aguardar"])
    st.markdown(f"### {cfg['emoji']} Recomendacao")
    getattr(st, cfg["cor"])(f"**{cfg['rotulo']}**\n\n{cfg['explicacao']}")
    if detalhe_extra:
        st.markdown(detalhe_extra)


# ============================================================
# EXECUCAO DA BUSCA
# ============================================================
if st.button(":mag: Buscar melhores ofertas no Google Flights", use_container_width=True):
    if not SERPAPI_KEY:
        st.error("Chave SERPAPI_KEY nao configurada nos Secrets do Streamlit.")
    else:
        st.divider()

        data_br_ida = data_ida.strftime("%d/%m/%Y")
        data_iso_ida = data_ida.strftime("%Y-%m-%d")
        titulo = f":round_pushpin: Busca real de {origem_iata} para {destino_iata} ({data_br_ida}) - classe {classe_cabine}"
        if tipo_viagem == "Ida e Volta" and data_volta:
            titulo += f" | Volta: {data_volta.strftime('%d/%m/%Y')}"
        st.subheader(titulo)

        # Estruturas normalizadas (Passo 3)
        ofertas_ida = []        # Estrategia A - so ida
        ofertas_volta = []      # Estrategia A - so volta
        ofertas_ida_volta = []  # Estrategia B - round-trip unificado

        with st.spinner("Consultando Google Flights (Estrategia A: trechos separados)..."):
            raw_ida = buscar_serpapi_oneway(origem_iata, destino_iata, data_ida, num_pax, classe_cabine)
            for i, opt in enumerate(raw_ida):
                n = normalizar_oferta_serp(opt, "ida", "A_separado", i)
                if n:
                    ofertas_ida.append(n)

            if tipo_viagem == "Ida e Volta" and data_volta:
                raw_volta = buscar_serpapi_oneway(destino_iata, origem_iata, data_volta, num_pax, classe_cabine)
                for i, opt in enumerate(raw_volta):
                    n = normalizar_oferta_serp(opt, "volta", "A_separado", i)
                    if n:
                        ofertas_volta.append(n)

        # Estrategia B: round-trip unificado (so faz sentido para ida e volta)
        if tipo_viagem == "Ida e Volta" and data_volta:
            with st.spinner("Consultando Google Flights (Estrategia B: ida e volta unificada)..."):
                raw_rt = buscar_serpapi_roundtrip(origem_iata, destino_iata, data_ida, data_volta, num_pax, classe_cabine)
                for i, opt in enumerate(raw_rt):
                    n = normalizar_oferta_serp(opt, "ida_volta", "B_unificado", i)
                    if n:
                        ofertas_ida_volta.append(n)

        # Resumo das buscas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.success(f"Estrategia A - Ida: {len(ofertas_ida)} opcoes")
        with c2:
            if tipo_viagem == "Ida e Volta" and data_volta:
                st.info(f"Estrategia A - Volta: {len(ofertas_volta)} opcoes")
            else:
                st.info("Estrategia A - Volta: n/a (somente ida)")
        with c3:
            if tipo_viagem == "Ida e Volta" and data_volta:
                st.warning(f"Estrategia B - Round-trip unico: {len(ofertas_ida_volta)} opcoes")
            else:
                st.info("Estrategia B - n/a (somente ida)")

        st.write("")

        if not ofertas_ida and not ofertas_ida_volta:
            st.warning("Nenhum voo encontrado no Google Flights para os parametros informados.")
        else:
            # ---- Bloco 1: Estrategia A - trechos separados ----
            if ofertas_ida:
                st.markdown("## :compass: Estrategia A - Trechos separados (Google Flights)")

                # Somente ida
                if tipo_viagem == "Somente Ida":
                    for o in ofertas_ida[:5]:
                        tag = ":trophy: MENOR TARIFA GOOGLE" if o["indice"] == 0 else ":white_check_mark: OPORTUNIDADE VALIDADA"
                        st.markdown(
                            f"### :airplane: {o['cia']}  "
                            f"<span style='background-color:#d4edda; color:#155724; "
                            f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                            unsafe_allow_html=True,
                        )
                        ca, cb, cc = st.columns([4, 4, 3])
                        with ca:
                            txt_voo = f" - Voo {o['num_voo']}" if o['num_voo'] else ""
                            st.info(
                                f"**:airplane: IDA ({data_br_ida})**{txt_voo}\n\n"
                                f"**{o['dep_iata']}** ({o['dep_time']}) -> **{o['arr_iata']}** ({o['arr_time']})\n\n"
                                f":stopwatch: Duracao: {o['duracao_fmt']} | Escalas: {o['escalas']}"
                            )
                        with cb:
                            st.warning(
                                f"**TARIFA DE REFERENCIA**\n\n"
                                f"### R$ {o['preco']:,.2f}\n"
                                f"Fonte: Google Flights ({o['tipo_token']})"
                            )
                        with cc:
                            st.write("")
                            st.write("")
                            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                            st.link_button("Comprar Voo :link:", link, use_container_width=True)
                        st.divider()

                # Ida e Volta combinados (soma das melhores de cada trecho)
                if tipo_viagem == "Ida e Volta" and data_volta and ofertas_volta:
                    data_br_volta = data_volta.strftime("%d/%m/%Y")
                    data_iso_volta = data_volta.strftime("%Y-%m-%d")
                    qtd = min(len(ofertas_ida), len(ofertas_volta), 5)
                    for i in range(qtd):
                        oi = ofertas_ida[i]
                        ov = ofertas_volta[i]
                        preco_total = oi['preco'] + ov['preco']
                        tag = ":trophy: MELHOR COMBINACAO GOOGLE" if i == 0 else ":white_check_mark: OPORTUNIDADE VALIDADA"
                        st.markdown(
                            f"### :airplane: {oi['cia']} / {ov['cia']}  "
                            f"<span style='background-color:#d4edda; color:#155724; "
                            f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                            unsafe_allow_html=True,
                        )
                        ca, cb, cc, cd = st.columns([3, 3, 3, 2])
                        with ca:
                            txt_i = f" - Voo {oi['num_voo']}" if oi['num_voo'] else ""
                            st.info(
                                f"**:airplane: IDA ({data_br_ida})**{txt_i}\n\n"
                                f"**{oi['dep_iata']}** ({oi['dep_time']}) -> **{oi['arr_iata']}** ({oi['arr_time']})"
                            )
                        with cb:
                            txt_v = f" - Voo {ov['num_voo']}" if ov['num_voo'] else ""
                            st.info(
                                f"**:airplane: VOLTA ({data_br_volta})**{txt_v}\n\n"
                                f"**{ov['dep_iata']}** ({ov['dep_time']}) -> **{ov['arr_iata']}** ({ov['arr_time']})"
                            )
                        with cc:
                            st.warning(
                                f"**TARIFA TOTAL COMBINADA**\n\n"
                                f"### R$ {preco_total:,.2f}\n"
                                f"Fonte: Google Flights (soma de trechos)"
                            )
                        with cd:
                            st.write("")
                            st.write("")
                            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_iso_volta}"
                            st.link_button("Comprar Voo :link:", link, use_container_width=True)
                        st.divider()

            # ---- Bloco 2: Estrategia B - round-trip unificado ----
            if ofertas_ida_volta:
                st.write("")
                st.markdown("## :tickets: Estrategia B - Ida e volta unificada (Google Flights)")
                st.caption(
                    "Esta busca pede a tarifa de round-trip em uma unica consulta ao Google Flights. "
                    "Capta casos em que a tarifa de ida+volta sai mais barata comprada junto (ex.: LATAM)."
                )

                for o in ofertas_ida_volta[:5]:
                    tag = ":trophy: MELHOR TARIFA ROUND-TRIP" if o['indice'] == 0 else ":white_check_mark: OPORTUNIDADE VALIDADA"
                    st.markdown(
                        f"### :airplane: {o['cia']}  "
                        f"<span style='background-color:#cce5ff; color:#004085; "
                        f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                        unsafe_allow_html=True,
                    )
                    ca, cb, cc = st.columns([4, 4, 3])
                    with ca:
                        txt_voo = f" - Voo {o['num_voo']}" if o['num_voo'] else ""
                        st.info(
                            f"**:airplane: IDA + VOLTA**{txt_voo}\n\n"
                            f"**{o['dep_iata']}** ({o['dep_time']}) -> **{o['arr_iata']}** ({o['arr_time']})\n\n"
                            f":stopwatch: Duracao total ida: {o['duracao_fmt']} | Escalas: {o['escalas']}"
                        )
                    with cb:
                        st.warning(
                            f"**TARIFA ROUND-TRIP**\n\n"
                            f"### R$ {o['preco']:,.2f}\n"
                            f"Fonte: Google Flights ({o['tipo_token']})"
                        )
                    with cc:
                        st.write("")
                        st.write("")
                        link = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}%20through%20{data_volta.strftime('%Y-%m-%d')}"
                        st.link_button("Comprar Voo :link:", link, use_container_width=True)
                    st.divider()

            # ---- Passo 5: Recomendacao (framework) ----
            st.write("")
            st.markdown("## :bulb: Recomendacao Cash vs Milhas")
            st.caption(
                "Framework de decisao montado. A logica que compara valor de milha sera "
                "ativada no Passo 6, quando integrarmos o API de passagens em milhas."
            )

            # Calcular a melhor tarifa cash encontrada (referencia para o futuro)
            todas_cash = [o['preco'] for o in ofertas_ida]
            if ofertas_ida_volta:
                todas_cash += [o['preco'] for o in ofertas_ida_volta]
            if todas_cash:
                melhor_cash = min(todas_cash)
                st.info(f"**Melhor tarifa em dinheiro encontrada:** R$ {melhor_cash:,.2f}")

            # Placeholder: ate o Passo 6, sempre exibe o estado "aguardar"
            # com explicacao de que a comparacao de milhas ainda nao esta ativa.
            exibir_recomendacao(
                "aguardar",
                detalhe_extra=(
                    "_Lado milhas ainda nao conectado._ "
                    "No proximo passo vamos integrar o API de milhas para calcular "
                    "os centavos por milha e decidir automaticamente entre os tres estados."
                ),
            )
