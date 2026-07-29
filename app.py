# -*- coding: utf-8 -*-
"""
Caçador Particular de Passagens & Milhas
========================================
Busca em tempo real no Google Flights (SerpApi) com duas estratégias:
  A) Trechos separados (ida + volta independentes)
  B) Ida e volta unificada (round-trip único)

Resultado normalizado em estrutura única.
Framework de recomendação cash vs milhas pronto para API de milhas.
"""

import datetime
from serpapi import GoogleSearch
import streamlit as st


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Caçador de Passagens - Multi-Estratégia",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption(
    "Busca em tempo real no Google Flights (SerpApi) — "
    "Estratégia A: trechos separados | Estratégia B: ida e volta unificada"
)


# ============================================================
# SECRETS
# ============================================================
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")


# ============================================================
# DICIONÁRIO DE AEROPORTOS
# ============================================================
AEROPORTOS = {
    "São Paulo - Todos os Aeroportos (SAO)": "SAO",
    "São Paulo - Guarulhos (GRU)": "GRU",
    "São Paulo - Congonhas (CGH)": "CGH",
    "São Paulo - Viracopos / Campinas (VCP)": "VCP",
    "Rio de Janeiro - Todos os Aeroportos (RIO)": "RIO",
    "Rio de Janeiro - Galeão (GIG)": "GIG",
    "Rio de Janeiro - Santos Dumont (SDU)": "SDU",
    "Belo Horizonte - Confins (CNF)": "CNF",
    "Belo Horizonte - Pampulha (PLU)": "PLU",
    "Brasília (BSB)": "BSB",
    "Salvador (SSA)": "SSA",
    "Recife (REC)": "REC",
    "Fortaleza (FOR)": "FOR",
    "Porto Alegre (POA)": "POA",
    "Curitiba (CWB)": "CWB",
    "Florianópolis (FLN)": "FLN",
    "Manaus (MAO)": "MAO",
    "Belém (BEL)": "BEL",
    "Goiânia (GYN)": "GYN",
    "Vitória (VIX)": "VIX",
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
# OPÇÕES SUPERIORES DE FILTRO
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
        format_func=lambda x: {
            "economy": "Econômica",
            "business": "Executiva",
            "first": "Primeira Classe",
        }[x],
    )

st.write("")


# ============================================================
# FORMULÁRIO DE BUSCA
# ============================================================
col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
    origem_sel = st.selectbox("✈️ Origem", options=lista_opcoes_aeroportos, index=1)
    origem_iata = AEROPORTOS[origem_sel]

with col2:
    destino_sel = st.selectbox("✈️ Destino", options=lista_opcoes_aeroportos, index=5)
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
# NORMALIZAÇÃO EM ESTRUTURA ÚNICA
# ============================================================
def formatar_duracao(minutos):
    if not minutos:
        return "N/A"
    return f"{minutos // 60}h {minutos % 60}m"


def normalizar_oferta_serp(flight_option, trecho, estrategia, indice):
    """Converte oferta bruta do Google Flights em dicionário padronizado."""
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
        cia = cia_primeiro or cia_ultimo or "Companhia Aérea"

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

    tipo_token = flight_option.get("type", "other_flights")

    return {
        "fonte": "Google Flights",
        "estrategia": estrategia,  # A_separado | B_unificado
        "trecho": trecho,          # ida | volta | ida_volta
        "indice": indice,
        "tipo_token": "Melhor" if tipo_token == "best_flights" else "Outra",
        "cia": cia,
        "num_voo": num_voo,
        "escalas": escalas,
        "duracao_min": duracao_min,
        "duracao_fmt": formatar_duracao(duracao_min),
        "dep_iata": dep_airport.get("id", ""),
        "dep_time": dep_time,
        "arr_iata": arr_airport.get("id", ""),
        "arr_time": arr_time,
        "preco": float(preco) if preco is not None else 0.0,
        "moeda": moeda,
        "raw": flight_option,
    }


# ============================================================
# BUSCAS SERPAPI
# ============================================================
# No engine google_flights, travel_class deve ser NUMÉRICO:
# 1=econômica, 2=premium economy, 3=executiva, 4=primeira.
CLASSES_SERPAPI = {
    "economy": 1,
    "premium_economy": 2,
    "business": 3,
    "first": 4,
}


def _executar_serpapi(params, label_busca):
    """Executa a consulta e preserva o motivo quando a SerpApi não devolve voos."""
    try:
        results = GoogleSearch(params).get_dict()

        # Erro explícito da SerpApi (chave inválida, créditos, parâmetro, etc.)
        if results.get("error"):
            return [], str(results["error"])

        todas = []
        for item in results.get("best_flights", []) or []:
            item = dict(item)
            item["type"] = "best_flights"
            todas.append(item)
        for item in results.get("other_flights", []) or []:
            item = dict(item)
            item["type"] = "other_flights"
            todas.append(item)

        if not todas:
            chaves = ", ".join(sorted(results.keys())) if isinstance(results, dict) else "n/a"
            return [], (
                "A SerpApi respondeu sem opções de voo para esta consulta. "
                f"Chaves retornadas: {chaves}. "
                "Pode não haver disponibilidade para a data/filtros informados, "
                "ou a conta SerpApi pode estar sem créditos / sem o engine Google Flights."
            )
        return todas, None
    except Exception as e:
        return [], f"Erro técnico na consulta {label_busca}: {e}"


def _params_base_serpapi(dep_iata, arr_iata, data_ida, adultos, classe):
    return {
        "engine": "google_flights",
        "departure_id": dep_iata,
        "arrival_id": arr_iata,
        "outbound_date": data_ida.strftime("%Y-%m-%d"),
        "currency": "BRL",
        "hl": "pt-BR",
        "gl": "br",
        "adults": int(adultos),
        "travel_class": CLASSES_SERPAPI.get(classe, 1),
        "api_key": SERPAPI_KEY,
    }


def buscar_serpapi_oneway(dep_iata, arr_iata, data_obj, adultos, classe):
    """Estratégia A: busca um trecho isolado (somente ida)."""
    if not SERPAPI_KEY:
        return [], "SERPAPI_KEY não configurada."
    params = _params_base_serpapi(dep_iata, arr_iata, data_obj, adultos, classe)
    params["type"] = 2  # somente ida
    return _executar_serpapi(params, f"ida {dep_iata}-{arr_iata}")


def buscar_serpapi_roundtrip(dep_iata, arr_iata, data_ida_obj, data_volta_obj, adultos, classe):
    """Estratégia B: ida e volta na mesma tarifa."""
    if not SERPAPI_KEY:
        return [], "SERPAPI_KEY não configurada."
    params = _params_base_serpapi(dep_iata, arr_iata, data_ida_obj, adultos, classe)
    params["type"] = 1  # ida e volta
    params["return_date"] = data_volta_obj.strftime("%Y-%m-%d")
    return _executar_serpapi(params, f"ida e volta {dep_iata}-{arr_iata}")


# ============================================================
# RECOMENDAÇÃO (FRAMEWORK — AGUARDANDO API DE MILHAS)
# ============================================================
ESTADOS_RECOMENDACAO = {
    "milhas": {
        "emoji": "✨",
        "rotulo": "VALE EMITIR COM MILHAS",
        "cor": "success",
        "explicacao": (
            "A emissão em milhas oferece o melhor custo-benefício para esta rota. "
            "Verifique a disponibilidade de assentos no programa indicado."
        ),
    },
    "dinheiro": {
        "emoji": "💸",
        "rotulo": "MELHOR PAGAR EM DINHEIRO",
        "cor": "warning",
        "explicacao": (
            "O valor da milha nesta rota está baixo. "
            "Pagar em dinheiro preserva seus pontos para oportunidades melhores."
        ),
    },
    "aguardar": {
        "emoji": "⏳",
        "rotulo": "AGUARDAR TRANSFERÊNCIA BONIFICADA OU ALERTA DE DISPONIBILIDADE",
        "cor": "info",
        "explicacao": (
            "Nenhum dos lados está claramente vantajoso agora. "
            "Recomendado aguardar bônus de transferência de pontos ou alerta de "
            "disponibilidade de assentos em classe premium."
        ),
    },
}


def exibir_recomendacao(estado, detalhe_extra=None):
    """Exibe o card de recomendação na UI."""
    cfg = ESTADOS_RECOMENDACAO.get(estado, ESTADOS_RECOMENDACAO["aguardar"])
    st.markdown(f"### {cfg['emoji']} Recomendação")
    getattr(st, cfg["cor"])(f"**{cfg['rotulo']}**\n\n{cfg['explicacao']}")
    if detalhe_extra:
        st.markdown(detalhe_extra)


# ============================================================
# EXECUÇÃO DA BUSCA
# ============================================================
if st.button("🔍 Buscar melhores ofertas no Google Flights", use_container_width=True):
    if not SERPAPI_KEY:
        st.error("Chave SERPAPI_KEY não configurada nos Secrets do Streamlit.")
    else:
        st.divider()

        data_br_ida = data_ida.strftime("%d/%m/%Y")
        data_iso_ida = data_ida.strftime("%Y-%m-%d")
        titulo = (
            f"📍 Busca real de {origem_iata} para {destino_iata} "
            f"({data_br_ida}) — classe {classe_cabine}"
        )
        if tipo_viagem == "Ida e Volta" and data_volta:
            titulo += f" | Volta: {data_volta.strftime('%d/%m/%Y')}"
        st.subheader(titulo)

        ofertas_ida = []
        ofertas_volta = []
        ofertas_ida_volta = []
        erro_ida = None
        erro_volta = None
        erro_rt = None

        with st.spinner("Consultando Google Flights (Estratégia A: trechos separados)..."):
            raw_ida, erro_ida = buscar_serpapi_oneway(
                origem_iata, destino_iata, data_ida, num_pax, classe_cabine
            )
            for i, opt in enumerate(raw_ida):
                n = normalizar_oferta_serp(opt, "ida", "A_separado", i)
                if n:
                    ofertas_ida.append(n)

            if tipo_viagem == "Ida e Volta" and data_volta:
                raw_volta, erro_volta = buscar_serpapi_oneway(
                    destino_iata, origem_iata, data_volta, num_pax, classe_cabine
                )
                for i, opt in enumerate(raw_volta):
                    n = normalizar_oferta_serp(opt, "volta", "A_separado", i)
                    if n:
                        ofertas_volta.append(n)

        if tipo_viagem == "Ida e Volta" and data_volta:
            with st.spinner("Consultando Google Flights (Estratégia B: ida e volta unificada)..."):
                raw_rt, erro_rt = buscar_serpapi_roundtrip(
                    origem_iata, destino_iata, data_ida, data_volta, num_pax, classe_cabine
                )
                for i, opt in enumerate(raw_rt):
                    n = normalizar_oferta_serp(opt, "ida_volta", "B_unificado", i)
                    if n:
                        ofertas_ida_volta.append(n)

        # Diagnóstico: mostra o motivo real se a SerpApi falhar
        erros_busca = [
            ("Ida", erro_ida),
            ("Volta", erro_volta),
            ("Ida e volta unificada", erro_rt),
        ]
        for nome_busca, erro in erros_busca:
            if erro:
                st.warning(f"**{nome_busca}:** {erro}")

        # Resumo das buscas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.success(f"Estratégia A — Ida: {len(ofertas_ida)} opções")
        with c2:
            if tipo_viagem == "Ida e Volta" and data_volta:
                st.info(f"Estratégia A — Volta: {len(ofertas_volta)} opções")
            else:
                st.info("Estratégia A — Volta: n/a (somente ida)")
        with c3:
            if tipo_viagem == "Ida e Volta" and data_volta:
                st.warning(f"Estratégia B — Round-trip único: {len(ofertas_ida_volta)} opções")
            else:
                st.info("Estratégia B — n/a (somente ida)")

        st.write("")

        if not ofertas_ida and not ofertas_ida_volta:
            st.warning("Nenhum voo encontrado no Google Flights para os parâmetros informados.")
            st.info(
                "Checklist rápido:\n"
                "1. Confirme se `SERPAPI_KEY` está nos Secrets do Streamlit.\n"
                "2. Confirme se a conta SerpApi tem créditos e o engine Google Flights liberado.\n"
                "3. Tente uma data mais próxima (ex.: daqui 14–30 dias).\n"
                "4. Teste também origem SAO / destino RIO (multi-aeroporto)."
            )
        else:
            # ---- Bloco 1: Estratégia A ----
            if ofertas_ida:
                st.markdown("## 🧭 Estratégia A — Trechos separados (Google Flights)")

                if tipo_viagem == "Somente Ida":
                    for o in ofertas_ida[:5]:
                        tag = "🏆 MENOR TARIFA GOOGLE" if o["indice"] == 0 else "✅ OPORTUNIDADE VALIDADA"
                        st.markdown(
                            f"### ✈️ {o['cia']}  "
                            f"<span style='background-color:#d4edda; color:#155724; "
                            f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                            unsafe_allow_html=True,
                        )
                        ca, cb, cc = st.columns([4, 4, 3])
                        with ca:
                            txt_voo = f" • Voo {o['num_voo']}" if o["num_voo"] else ""
                            st.info(
                                f"**✈️ IDA ({data_br_ida})**{txt_voo}\n\n"
                                f"**{o['dep_iata']}** ({o['dep_time']}) → "
                                f"**{o['arr_iata']}** ({o['arr_time']})\n\n"
                                f"⏱️ Duração: {o['duracao_fmt']} | Escalas: {o['escalas']}"
                            )
                        with cb:
                            st.warning(
                                f"**TARIFA DE REFERÊNCIA**\n\n"
                                f"### R$ {o['preco']:,.2f}\n"
                                f"Fonte: Google Flights ({o['tipo_token']})"
                            )
                        with cc:
                            st.write("")
                            st.write("")
                            link = (
                                f"https://www.google.com/travel/flights"
                                f"?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                            )
                            st.link_button("Comprar Voo 🔗", link, use_container_width=True)
                        st.divider()

                if tipo_viagem == "Ida e Volta" and data_volta and ofertas_volta:
                    data_br_volta = data_volta.strftime("%d/%m/%Y")
                    data_iso_volta = data_volta.strftime("%Y-%m-%d")
                    qtd = min(len(ofertas_ida), len(ofertas_volta), 5)
                    for i in range(qtd):
                        oi = ofertas_ida[i]
                        ov = ofertas_volta[i]
                        preco_total = oi["preco"] + ov["preco"]
                        tag = "🏆 MELHOR COMBINAÇÃO GOOGLE" if i == 0 else "✅ OPORTUNIDADE VALIDADA"
                        st.markdown(
                            f"### ✈️ {oi['cia']} / {ov['cia']}  "
                            f"<span style='background-color:#d4edda; color:#155724; "
                            f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                            unsafe_allow_html=True,
                        )
                        ca, cb, cc, cd = st.columns([3, 3, 3, 2])
                        with ca:
                            txt_i = f" • Voo {oi['num_voo']}" if oi["num_voo"] else ""
                            st.info(
                                f"**✈️ IDA ({data_br_ida})**{txt_i}\n\n"
                                f"**{oi['dep_iata']}** ({oi['dep_time']}) → "
                                f"**{oi['arr_iata']}** ({oi['arr_time']})"
                            )
                        with cb:
                            txt_v = f" • Voo {ov['num_voo']}" if ov["num_voo"] else ""
                            st.info(
                                f"**✈️ VOLTA ({data_br_volta})**{txt_v}\n\n"
                                f"**{ov['dep_iata']}** ({ov['dep_time']}) → "
                                f"**{ov['arr_iata']}** ({ov['arr_time']})"
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
                            link = (
                                f"https://www.google.com/travel/flights"
                                f"?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}"
                                f"%20on%20{data_iso_ida}%20through%20{data_iso_volta}"
                            )
                            st.link_button("Comprar Voo 🔗", link, use_container_width=True)
                        st.divider()

            # ---- Bloco 2: Estratégia B ----
            if ofertas_ida_volta:
                st.write("")
                st.markdown("## 🎟️ Estratégia B — Ida e volta unificada (Google Flights)")
                st.caption(
                    "Esta busca pede a tarifa de round-trip em uma única consulta ao Google Flights. "
                    "Capta casos em que a tarifa de ida+volta sai mais barata comprada junta (ex.: LATAM)."
                )

                for o in ofertas_ida_volta[:5]:
                    tag = "🏆 MELHOR TARIFA ROUND-TRIP" if o["indice"] == 0 else "✅ OPORTUNIDADE VALIDADA"
                    st.markdown(
                        f"### ✈️ {o['cia']}  "
                        f"<span style='background-color:#cce5ff; color:#004085; "
                        f"padding:3px 8px; border-radius:5px; font-size:12px;'>{tag}</span>",
                        unsafe_allow_html=True,
                    )
                    ca, cb, cc = st.columns([4, 4, 3])
                    with ca:
                        txt_voo = f" • Voo {o['num_voo']}" if o["num_voo"] else ""
                        st.info(
                            f"**✈️ IDA + VOLTA**{txt_voo}\n\n"
                            f"**{o['dep_iata']}** ({o['dep_time']}) → "
                            f"**{o['arr_iata']}** ({o['arr_time']})\n\n"
                            f"⏱️ Duração total ida: {o['duracao_fmt']} | Escalas: {o['escalas']}"
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
                        link = (
                            f"https://www.google.com/travel/flights"
                            f"?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}"
                            f"%20on%20{data_iso_ida}%20through%20{data_volta.strftime('%Y-%m-%d')}"
                        )
                        st.link_button("Comprar Voo 🔗", link, use_container_width=True)
                    st.divider()

            # ---- Recomendação (framework) ----
            st.write("")
            st.markdown("## 💡 Recomendação Cash vs Milhas")
            st.caption(
                "Framework de decisão montado. A lógica que compara valor de milha será "
                "ativada no próximo passo, quando integrarmos a API de passagens em milhas."
            )

            todas_cash = [o["preco"] for o in ofertas_ida if o.get("preco")]
            if tipo_viagem == "Ida e Volta" and ofertas_ida and ofertas_volta:
                todas_cash.append(ofertas_ida[0]["preco"] + ofertas_volta[0]["preco"])
            if ofertas_ida_volta:
                todas_cash += [o["preco"] for o in ofertas_ida_volta if o.get("preco")]
            if todas_cash:
                melhor_cash = min(todas_cash)
                st.info(f"**Melhor tarifa em dinheiro encontrada:** R$ {melhor_cash:,.2f}")

            exibir_recomendacao(
                "aguardar",
                detalhe_extra=(
                    "_Lado milhas ainda não conectado._ "
                    "No próximo passo vamos integrar a API de milhas para calcular "
                    "os centavos por milha e decidir automaticamente entre os três estados."
                ),
            )
