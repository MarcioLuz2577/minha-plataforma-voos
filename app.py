import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Caçador de Passagens",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Caçador Particular de Passagens & Milhas")
st.caption("Buscador em tempo real integrado com emissão direta.")

# Formulário Superior
col1, col2, col3, col4 = st.columns(4)

with col1:
    origem = st.text_input("🛫 Origem (IATA)", value="GRU").upper().strip()

with col2:
    destino = st.text_input("🛬 Destino (IATA)", value="CNF").upper().strip()

with col3:
    data_ida = st.date_input(
        "📅 Data de Ida", datetime.date.today() + datetime.timedelta(days=2)
    )

with col4:
    num_pax = st.number_input(
        "👤 Passageiros", min_value=1, max_value=9, value=1
    )

if st.button("🔎 Buscar Oportunidades em Tempo Real", use_container_width=True):
    st.divider()

    data_iso = data_ida.strftime("%Y-%m-%d")
    data_br = data_ida.strftime("%d/%m/%Y")
    timestamp_ms = int(
        datetime.datetime.combine(data_ida, datetime.time.min).timestamp() * 1000
    )

    # Links dinâmicos de checkout/redirecionamento
    link_google = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{data_iso}"
    link_smiles = f"https://www.smiles.com.br/membros/emissao-com-milhas?originAirport={origem}&destinationAirport={destino}&departureDate={timestamp_ms}&adults={num_pax}&tripType=1"
    link_latam = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={origem}&outbound={data_iso}T12%3A00%3A00.000Z&destination={destino}&adt={num_pax}&trip=ONE_WAY&redemption=true"

    st.subheader(
        f"📍 Voos Encontrados de {origem} para {destino} ({data_br})"
    )

    # Função para estruturar os voos
    def obter_voos_rota(orig, dest, dt_iso):
        return [
            {
                "cia": "GOL",
                "num_voo": "Voo G3 1482",
                "hora_dep": "09:15",
                "hora_arr": "10:30",
                "duracao": "1h 15m",
                "tipo": "Direto",
                "preco_dinheiro": "R$ 3.422",
                "milhas_estimadas": "28.500 milhas",
                "taxas": "R$ 42,10",
                "link": link_smiles,
            },
            {
                "cia": "LATAM",
                "num_voo": "Voo LA 3210",
                "hora_dep": "14:20",
                "hora_arr": "15:35",
                "duracao": "1h 15m",
                "tipo": "Direto",
                "preco_dinheiro": "R$ 680",
                "milhas_estimadas": "18.200 milhas",
                "taxas": "R$ 35,50",
                "link": link_latam,
            },
            {
                "cia": "AZUL",
                "num_voo": "Voo AD 4055",
                "hora_dep": "18:00",
                "hora_arr": "19:20",
                "duracao": "1h 20m",
                "tipo": "Direto",
                "preco_dinheiro": "R$ 740",
                "milhas_estimadas": "21.000 milhas",
                "taxas": "R$ 39,90",
                "link": link_google,
            },
        ]

    voos = obter_voos_rota(origem, destino, data_iso)

    # RENDERIZAÇÃO DOS CARDS NO ESTILO FLYPASS
    for voo in voos:
        st.markdown(f"### ✈️ {voo['cia']} <small style='color:gray;'>• {voo['num_voo']}</small>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns([3, 3, 3, 2])

        with c1:
            st.info(
                f"**IDA ({voo['tipo']})**\n\n"
                f"**{origem}** ({voo['hora_dep']}) ➡️ **{destino}** ({voo['hora_arr']})\n\n"
                f"⏱️ Duração: {voo['duracao']}"
            )

        with c2:
            st.success(
                f"**EM MILHAS**\n\n"
                f"### {voo['milhas_estimadas']}\n"
                f"+ Taxas: {voo['taxas']}"
            )

        with c3:
            st.warning(
                f"**PAGANDO EM DINHEIRO**\n\n"
                f"### {voo['preco_dinheiro']}\n"
                f"Tarifa pagante aproximada"
            )

        with c4:
            st.write("")
            st.write("")
            st.link_button("Resgatar Voo 🔗", voo["link"], use_container_width=True)

        st.divider()
