import datetime
import streamlit as st

st.set_page_config(
    page_title="Caçador de Passagens", page_icon="✈️", layout="wide"
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption(
    "Pesquise oportunidades reais em dinheiro ou milhas com link direto de"
    " emissão."
)

# Formulário de entrada
col1, col2, col3, col4 = st.columns(4)

with col1:
  origem = st.text_input("🛫 Origem (Código IATA)", value="GRU").upper()

with col2:
  destino = st.text_input("🛬 Destino (Código IATA)", value="MIA").upper()

with col3:
  data_ida = st.date_input(
      "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=30)
  )

with col4:
  passageiros = st.number_input(
      "👤 Passageiros", min_value=1, max_value=9, value=1
  )

# Botão de busca
if st.button("🔎 Buscar Melhores Oportunidades Reais"):
  st.divider()
  st.subheader(
      f"📍 Resultados Reais para: {origem} ➡️ {destino} em"
      f" {data_ida.strftime('%d/%m/%Y')}"
  )

  data_str_iso = data_ida.strftime("%Y-%m-%d")
  data_str_br = data_ida.strftime("%d/%m/%Y")
  timestamp_ms = int(
      datetime.datetime.combine(data_ida, datetime.time.min).timestamp() * 1000
  )

  link_google = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{data_str_iso}"
  link_smiles = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem}&destinationAirport={destino}&departureDate={timestamp_ms}&adults={passageiros}&tripType=1"
  link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem}&outbound={data_str_iso}T12%3A00%3A00.000Z&destination={destino}&adt={passageiros}&trip=ONE_WAY&redemption=true"
  link_azul = f"https://www.voezul.com.br/br/pt/home/selecao-voos?o1={origem}&d1={destino}&d1d={data_str_br}&p1={passageiros}&points=true"

  col_a, col_b = st.columns(2)

  with col_a:
    st.markdown("### 💵 Opções em Dinheiro")
    st.info("Varredura completa em dezenas de cias aéreas e agências.")
    st.link_button("👉 Abrir Busca no Google Flights", link_google)

  with col_b:
    st.markdown("### 🎫 Opções em Milhas / Pontos")
    st.link_button("👉 Buscar na Smiles (GOL)", link_smiles)
    st.link_button("👉 Buscar no LATAM Pass", link_latam)
    st.link_button("👉 Buscar na Azul Fidelidade", link_azul)
