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

# Puxa a chave oculta configurada nos Secrets do Streamlit Cloud
SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")

# --- DICIONÁRIO DE AEROPORTOS ---
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

# --- OPÇÕES SUPERIORES DE FILTRO ---
col_opt1, col_opt2 = st.columns(2)

with col_opt1:
  tipo_viagem = st.radio(
      "Tipo de Viagem:",
      options=["Somente Ida", "Ida e Volta"],
      horizontal=True,
      index=0,
  )

with col_opt2:
  modalidade_busca = st.radio(
      "Buscar por:",
      options=["Dinheiro", "Milhas"],
      horizontal=True,
      index=0,
  )

st.write("")

# --- FORMULÁRIO DE BUSCA ---
col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])

with col1:
  origem_sel = st.selectbox(
      "🛫 Origem",
      options=lista_opcoes_aeroportos,
      index=1,  # GRU por padrão
      help="Digite a cidade ou código IATA",
  )
  origem_iata = AEROPORTOS[origem_sel]

with col2:
  destino_sel = st.selectbox(
      "🛬 Destino",
      options=lista_opcoes_aeroportos,
      index=5,  # GIG por padrão
      help="Digite a cidade ou código IATA",
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
    st.text_input("📅 Data de Volta", value="Apenas Ida", disabled=True)

with col5:
  num_pax = st.number_input(
      "👤 Passageiros", min_value=1, max_value=9, value=1
  )

# --- PROCESSAMENTO DA BUSCA ---
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

    titulo_busca = f"📍 Voos Reais de {origem_iata} para {destino_iata} ({data_br_ida}) • Busca em {modalidade_busca}"
    if tipo_viagem == "Ida e Volta" and data_volta:
      data_br_volta = data_volta.strftime("%d/%m/%Y")
      titulo_busca += f" | Volta: {data_br_volta}"

    st.subheader(titulo_busca)

    with st.spinner("Consultando dados reais em tempo real no Google Flights..."):
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

            # Voo de IDA
            voo_ida = flights_list[0]
            cia = voo_ida.get("airline", "Companhia Aérea")
            num_voo_ida = voo_ida.get("flight_number", "")
            orig_ida = voo_ida.get("departure_airport", {}).get("id", origem_iata)
            dest_ida = voo_ida.get("arrival_airport", {}).get("id", destino_iata)
            hora_dep_ida = voo_ida.get("departure_airport", {}).get("time", "").split()[-1]
            hora_arr_ida = voo_ida.get("arrival_airport", {}).get("time", "").split()[-1]
            duracao_ida_min = voo_ida.get("duration", 0)
            duracao_ida_fmt = f"{duracao_ida_min // 60}h {duracao_ida_min % 60}m" if duracao_ida_min else "N/A"

            # Preço total da opção
            preco_reais = flight_option.get("price", 0)

            # Cabeçalho do Card
            st.markdown(
                f"### ✈️ {cia} <small style='color:gray;'>• Voo IDA: {num_voo_ida}</small>",
                unsafe_allow_html=True,
            )

            # Monta o layout do card dependendo de ser Ida ou Ida e Volta
            if tipo_viagem == "Ida e Volta" and len(flights_list) > 1:
              # Voo de VOLTA
              voo_volta = flights_list[1]
              num_voo_volta = voo_volta.get("flight_number", "")
              orig_volta = voo_volta.get("departure_airport", {}).get("id", destino_iata)
              dest_volta = voo_volta.get("arrival_airport", {}).get("id", origem_iata)
              hora_dep_volta = voo_volta.get("departure_airport", {}).get("time", "").split()[-1]
              hora_arr_volta = voo_volta.get("arrival_airport", {}).get("time", "").split()[-1]
              duracao_volta_min = voo_volta.get("duration", 0)
              duracao_volta_fmt = f"{duracao_volta_min // 60}h {duracao_volta_min % 60}m" if duracao_volta_min else "N/A"

              c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

              with c1:
                st.info(
                    f"**🛫 IDA ({data_br_ida})**\n\n"
                    f"**{orig_ida}** ({hora_dep_ida}) ➡️ **{dest_ida}** ({hora_arr_ida})\n\n"
                    f"⏱️ Duração: {duracao_ida_fmt}"
                )

              with c2:
                st.info(
                    f"**🛬 VOLTA ({data_br_volta})**\n\n"
                    f"**{orig_volta}** ({hora_dep_volta}) ➡️ **{dest_volta}** ({hora_arr_volta})\n\n"
                    f"⏱️ Duração: {duracao_volta_fmt}"
                )

              with c3:
                st.warning(
                    f"**TARIFA TOTAL (IDA + VOLTA)**\n\n"
                    f"### R$ {preco_reais:,.2f}\n"
                    f"Tarifa pagante real (Google Flights)"
                )

              with c4:
                st.write("")
                st.write("")
                # Links de ação
                if modalidade_busca == "Milhas":
                  btn_texto = "Resgatar em Milhas 🔗"
                  if "GOL" in cia.upper():
                    link_acao = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem_iata}&destinationAirport={destino_iata}&departureDate={timestamp_ms_ida}&adults={num_pax}&tripType=2"
                  elif "LATAM" in cia.upper():
                    link_acao = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem_iata}&outbound={data_iso_ida}T12%3A00%3A00.000Z&destination={destino_iata}&adt={num_pax}&trip=ROUND_TRIP&redemption=true"
                  else:
                    link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                else:
                  btn_texto = "Comprar Voo 🔗"
                  link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"

                st.link_button(btn_texto, link_acao, use_container_width=True)

            else:
              # Somente Ida
              c1, c2, c3 = st.columns([4, 4, 3])

              with c1:
                st.info(
                    f"**🛫 IDA ({data_br_ida})**\n\n"
                    f"**{orig_ida}** ({hora_dep_ida}) ➡️ **{dest_ida}** ({hora_arr_ida})\n\n"
                    f"⏱️ Duração: {duracao_ida_fmt}"
                )

              with c2:
                st.warning(
                    f"**TARIFA EM DINHEIRO**\n\n"
                    f"### R$ {preco_reais:,.2f}\n"
                    f"Tarifa pagante real (Google Flights)"
                )

              with c3:
                st.write("")
                st.write("")
                if modalidade_busca == "Milhas":
                  btn_texto = "Resgatar em Milhas 🔗"
                  if "GOL" in cia.upper():
                    link_acao = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem_iata}&destinationAirport={destino_iata}&departureDate={timestamp_ms_ida}&adults={num_pax}&tripType=1"
                  elif "LATAM" in cia.upper():
                    link_acao = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem_iata}&outbound={data_iso_ida}T12%3A00%3A00.000Z&destination={destino_iata}&adt={num_pax}&trip=ONE_WAY&redemption=true"
                  else:
                    link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"
                else:
                  btn_texto = "Comprar Voo 🔗"
                  link_acao = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_iata}%20from%20{origem_iata}%20on%20{data_iso_ida}"

                st.link_button(btn_texto, link_acao, use_container_width=True)

            st.divider()

      except Exception as e:
        st.error(f"Erro ao buscar voos reais: {e}")
