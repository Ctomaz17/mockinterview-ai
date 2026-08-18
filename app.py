import streamlit as st
from openai import OpenAI
import PyPDF2
import os
import sqlite3
import pandas as pd
import datetime
import re
import io

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="MockInterview AI Pro", page_icon="", layout="wide")

# Inicializa Banco de Dados Local (SQLite)
def init_db():
    conn = sqlite3.connect("historico_entrevistas.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            modo TEXT,
            cargo TEXT,
            nota INTEGER,
            resumo_feedback TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# --- AUTENTICAÇÃO DA API - VERSÃO CORRIGIDA ---
st.title("🚀 MockInterview AI Pro")

# Verifica se há uma chave API configurada
if "api_key_configurada" not in st.session_state:
    st.session_state.api_key_configurada = False

# Tenta pegar a chave dos secrets (Streamlit Cloud)
if not st.session_state.api_key_configurada:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.session_state.api_key_configurada = True
        st.session_state.api_key = api_key
    except:
        # Se não encontrar nos secrets, pede ao usuário
        pass

# Se ainda não tem chave, mostra o input
if not st.session_state.api_key_configurada:
    api_key_input = st.text_input("🔑 Por favor, insira sua chave API da OpenAI:", type="password", key="api_input")
    if api_key_input and api_key_input.startswith("sk-"):
        st.session_state.api_key = api_key_input
        st.session_state.api_key_configurada = True
        st.success("✅ Chave configurada! Recarregue a página para continuar.")
        st.stop()
    elif api_key_input and not api_key_input.startswith("sk-"):
        st.error("️ A chave deve começar com 'sk-'")
        st.stop()
    else:
        st.info(" Insira sua chave acima para começar")
        st.stop()

# Inicializa o cliente OpenAI
client = OpenAI(api_key=st.session_state.api_key)

# Restante do código continua igual...
# (vou mandar as próximas partes)
