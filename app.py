import datetime
from serpapi import GoogleSearch
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Caçador de Passagens",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption("Resultados 100% reais consultados em tempo real via SerpApi.")

# Puxa a chave oculta configurada nos Secrets
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")

# --- DICIONÁRIO DE AEROPORTOS (Busca por Cidade, Código ou Nome) ---
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

# --- INTERFACE DO USUÁRIO ---

# 1. Tipo de Viagem
tipo_viagem = st.radio(
    "Tipo de Viagem:",
    options=["Somente Ida", "Ida e Volta"],
    horizontal=True,
    index=0,
)

st.write("")

# 2. Formulário de Busca com Dropdown Autocomplete
col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
  origem_sel = st.selectbox(
      "🛫 Origem",
      options=lista_opcoes_aeroportos,
      index=1,  # Padrão: GRU
      help="Digite a cidade ou código IATA (ex: São Paulo, GRU, Galeão...)",
  )
  origem_iata = AEROPORTOS[origem_sel]

with col2:
  destino_sel = st.selectbox(
      "🛬 Destino",
      options=lista_opcoes_aeroportos,
      index=5,  # Padrão: GIG
      help="Digite a cidade ou código IATA (ex: Rio, GIG, CNF...)",
  )
  destino_iata = AEROPORTOS[destino_sel]

with col3:
  data_ida = st.date_input(
      "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=7)
  )

with col4:
  if tipo_viagem == "Ida e Volta":
    data_volta = st.date_input(
        "📅 Data de Volta", data_ida + datetime.timedelta(days=7)
    )
  else:
    data_volta = None
    st.text_input(
        "📅 Data de Volta",
        value="Apenas Ida",
        disabled=True,
    )

with col5:
  num_pax = st.number_input(
      "👤 Passageiros", min_value=1, max_value=9, value=1
  )


# --- PROCESSAMENTO DA BUSCA REAL ---
if st.button("🔎 Buscar Oportunidades Reais", use_container_width=True):
  if not SERPAPI_KEY:
    st.error(
        "⚠️ Chave da SerpApi não encontrada nos Secrets do Streamlit Cloud."
    )
  else:
    st.divider()
    data_iso_ida = data_ida.strftime("%Y-%m-%d")
    data_br_ida = data_ida.strftime("%d/%m/%Y")
    timestamp_ms_ida = int(
        datetime.datetime.combine(data_ida, datetime.time.min).timestamp()
        * 1000
    )

    titulo_busca = (
        f"📍 Voos Reais de {origem_iata} para {destino_iata} ({data_br_ida})"
    )
    if tipo_viagem == "Ida e Volta" and data_volta:
      data_br_volta = data_volta.strftime("%d/%m/%Y")
      titulo_busca += f" | Volta: {data_br_volta}"

    st.subheader(titulo_busca)

    with st.spinner("Consultando dados reais em tempo real no Google Flights..."):
      # Define o tipo para a API (1 = Ida e Volta, 2 = Somente Ida)
      type_param = "1" if tipo_viagem == "Ida e Volta" else "2"

      params = {
          "engine": "google_flights",
          "departure_id": origem_iata,
          "arrival_id": destino_iata,
          "outbound_date": data_iso_ida,
          "currency": "BRL",
          "hl": "pt",
          "type": type_param,
          "adults": int(num_pax),
          "api_key": SERPAPI_KEY,
      }

      if tipo_viagem == "Ida e Volta" and data_volta:
        params["return_date"] = data_volta.strftime("%Y-%m-%d")

      try:
        search = GoogleSearch(params)
        results = search.get_dict()

        all_flights = []
        if "best_flights" in results:
          all_flights.extend(results["best_flights"])
        if "other_flights" in results:
          all_flights.extend(results["other_flights"])

        if not all_flights:
          st.warning(
              "Nenhum voo real encontrado para a rota e datas selecionadas."
          )
        else:
          for flight_option in all_flights[:5]:
            flights_list = flight_option.get("flights", [])
            if not flights_list:
              continue

            first_flight = flights_list[0]
            last_flight = flights_list[-1]

            cia = first_flight.get("airline", "Companhia Aérea")
            num_voo = first_flight.get("flight_number", "")

            hora_dep = (
                first_flight.get("departure_airport", {})
                .get("time", "")
                .split()[-1]
            )
            hora_arr = (
                last_flight.get("arrival_airport", {}).get("time", "").split()[-1]
            )

            duracao_min = flight_option.get("total_duration", 0)
            duracao_fmt = (
                f"{duracao_min // 60}h {duracao_min % 60}m"
                if duracao_min
                else "N/A"
            )
            preco_reais = flight_option.get("price", 0)

            tipo_rota = (
                "Direto" if len(flights_list) == 1 else f"{len(flights_list)-1} parada(s)"
            )

            # Estimativa de milhas (base proporcional R$ 20 / 1.000 milhas)
            milhas_est = (
                f"{int((preco_reais / 20) * 1000):,} milhas".replace(",", ".")
                if preco_reais
                else "Consulte"
            )

            # Links diretos para checkout oficial
            if "GOL" in cia.upper():
              link_resgate = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem_iata}&destinationAirport={destino_iata}&departureDate={timestamp_ms_ida}&adults={num_pax}&tripType=1"
            elif "LATAM" in cia.upper():
              link_resgate = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem_iata}&outbound={data_iso_ida}T12%3A00%3A00.000Z&destination={destino_iata}&adt={num_pax}&trip=ONE_WAY&redemption=true"
            elif "AZUL" in cia.upper():
              link_resgate = f"https://www.voezul.com.br/br/pt/home/selecao-voos?o1={origem_iata}&d1={destino_iata}&v1={data_iso_ida}&p1={num_pax}"
            else:
              link_resgate = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"

            # Renderização dos Cards na Interface
            st.markdown(
                f"### ✈️ {cia} <small style='color:gray;'>• Voo"
                f" {num_voo}</small>",
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

            with c1:
              st.info(
                  f"**{tipo_viagem.upper()} ({tipo_rota})**\n\n"
                  f"**{origem_iata}** ({hora_dep}) ➡️ **{destino_iata}** ({hora_arr})\n\n"
                  f"⏱️ Duração Total: {duracao_fmt}"
              )

            with c2:
              st.success(
                  f"**ESTIMATIVA EM MILHAS**\n\n"
                  f"### {milhas_est}\n"
                  f"+ Taxas de embarque oficiais"
              )

            with c3:
              st.warning(
                  f"**PAGANDO EM DINHEIRO**\n\n"
                  f"### R$ {preco_reais:,.2f}\n"
                  f"Tarifa pagante real (Google Flights)"
              )

            with c4:
              st.write("")
              st.write("")
              st.link_button(
                  "Resgatar Voo 🔗", link_resgate, use_container_width=True
              )

            st.divider()

      except Exception as e:
        st.error(f"Erro ao buscar voos reais: {e}")
