import streamlit as st
from openai import OpenAI
import PyPDF2
import os
import sqlite3
import pandas as pd
import datetime
import re
from streamlit_mic_recorder import mic_recorder

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="MockInterview AI Pro", page_icon="🚀", layout="wide")

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

# --- AUTENTICAÇÃO DA API ---
api_key = os.getenv("OPENAI_API_KEY") or st.text_input("🔑 Chave API OpenAI:", type="password")
if not api_key:
    st.stop()
client = OpenAI(api_key=api_key)

# --- FUNÇÕES AUXILIARES ---
def extrair_texto_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = "".join(page.extract_text() or "" for page in reader.pages)
        return texto.strip()
    except Exception as e:
        st.error(f"Erro ao ler PDF: {e}")
        return None

def salvar_no_historico(modo, cargo, nota, resumo):
    conn = sqlite3.connect("historico_entrevistas.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO historico (data, modo, cargo, nota, resumo_feedback) VALUES (?, ?, ?, ?, ?)",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), modo, cargo, nota, resumo)
    )
    conn.commit()
    conn.close()

def extrair_nota(texto_resposta):
    # Tenta encontrar um padrão como "SCORE: 85" ou "Nota: 85" no final do texto
    match = re.search(r"(?:SCORE|Nota|Nota Final)[:\s]*(\d{1,3})", texto_resposta, re.IGNORECASE)
    return int(match.group(1)) if match else None

# --- INTERFACE PRINCIPAL ---
st.title("🚀 MockInterview AI Pro")
st.markdown("Plataforma completa de **Treinamento de Inglês** e **Triagem de RH** com Inteligência Artificial.")

with st.sidebar:
    st.header("⚙️ Configurações")
    modo_app = st.radio("Selecione o Modo de Uso:", ["🎓 Modo Aluno (Prática)", "🏢 Modo RH (Triagem)"])
    
    st.divider()
    st.subheader("📄 Dados")
    uploaded_file = st.file_uploader("Upload do Currículo (PDF)", type=["pdf"])
    job_description = st.text_area("Descrição da Vaga (Job Description)", height=150)
    
    if st.button("🗑️ Limpar Tudo e Reiniciar", type="primary"):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    if st.button("📊 Ver Meu Histórico"):
        st.session_state.mostrar_historico = True

# --- LÓGICA DO MODO ALUNO ---
if modo_app == "🎓 Modo Aluno (Prática)":
    st.info("💡 Dica: Use o microfone abaixo para praticar sua pronúncia em inglês!")
    
    if uploaded_file and job_description:
        cv_text = extrair_texto_pdf(uploaded_file)
        if not cv_text:
            st.stop()

        system_prompt = f"""
        You are an expert HR Recruiter conducting a mock interview in ENGLISH.
        CV: {cv_text}
        JOB: {job_description}
        RULES:
        1. Ask ONE question at a time. Wait for the answer.
        2. After exactly 3 questions, end the interview.
        3. At the end, output EXACTLY "INTERVIEW_COMPLETE" followed by a detailed feedback in PORTUGUESE.
        4. The feedback MUST include: Grammar/Vocab corrections, Soft Skills evaluation, 3 actionable tips, and at the very end, a line formatted exactly as "SCORE: [0-100]".
        """

        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": system_prompt}]
            st.session_state.interview_ended = False
            
            # Primeira pergunta da IA
            with st.chat_message("assistant"):
                with st.spinner("Preparando sua entrevista..."):
                    response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.messages)
                    msg = response.choices[0].message.content
                    st.markdown(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                    
                    # TTS: Gerar áudio da pergunta (opcional, melhora a imersão)
                    try:
                        audio_response = client.audio.speech.create(model="tts-1", voice="alloy", input=msg)
                        st.audio(audio_response.content, format="audio/mp3")
                    except:
                        pass

        # Exibir histórico de chat
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Entrada do Usuário (Texto ou Áudio)
        if not st.session_state.get("interview_ended", False):
            col1, col2 = st.columns([3, 1])
            with col1:
                prompt_text = st.chat_input("Digite sua resposta em inglês...")
            with col2:
                # Gravação de Áudio
                audio_value = mic_recorder(start_prompt="🎙️ Gravar", stop_prompt="⏹️ Parar", key="mic")
            
            prompt = prompt_text
            if audio_value and audio_value.get("bytes"):
                # Speech-to-Text usando Whisper
                with st.spinner("Transcrevendo áudio..."):
                    import io
                    audio_file = io.BytesIO(audio_value["bytes"])
                    audio_file.name = "resposta.mp3"
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                    prompt = transcript.text
                    st.success(f"🎤 Transcrição: '{prompt}'")

            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(f"🗣️ {prompt}")
                
                with st.chat_message("assistant"):
                    with st.spinner("Analisando sua resposta..."):
                        response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.messages)
                        msg = response.choices[0].message.content
                        st.markdown(msg)
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                        
                        if "INTERVIEW_COMPLETE" in msg:
                            st.session_state.interview_ended = True
                            nota = extrair_nota(msg)
                            salvar_no_historico("Aluno", "Prática Geral", nota or 0, msg[:200] + "...")
                            st.success("🎉 Entrevista finalizada! Sua nota e feedback foram salvos no histórico.")
                            st.rerun()
    else:
        st.warning("⚠️ Faça o upload do currículo e da descrição da vaga na barra lateral para começar.")

# --- LÓGICA DO MODO RH ---
elif modo_app == "🏢 Modo RH (Triagem)":
    st.header("Análise Automatizada de Candidatos")
    if st.button("🔍 Analisar Candidato Agora", type="primary"):
        if not uploaded_file or not job_description:
            st.error("Por favor, forneça o currículo e a descrição da vaga.")
        else:
            cv_text = extrair_texto_pdf(uploaded_file)
            if not cv_text:
                st.stop()
            
            prompt_rh = f"""
            Você é um especialista em RH de uma multinacional. Analise o currículo abaixo em relação à descrição da vaga.
            Retorne a análise ESTRITAMENTE EM PORTUGUÊS e no seguinte formato Markdown:
            
            ### 📊 Nota de Compatibilidade: [0-100]
            ### ✅ Pontos Fortes (Top 3)
            ### ⚠️ Pontos de Atenção / Lacunas (Top 3)
            ### 💡 Recomendação Final (Contratar, Entrevistar ou Rejeitar) e justificativa.
            
            CV: {cv_text}
            VAGA: {job_description}
            """
            
            with st.spinner("A IA está analisando o perfil do candidato..."):
                response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt_rh}])
                resultado = response.choices[0].message.content
                st.markdown(resultado)
                
                nota = extrair_nota(resultado)
                cargo_match = re.search(r"Vaga[:\s]*(.+)", job_description.split('\n')[0], re.IGNORECASE)
                cargo = cargo_match.group(1) if cargo_match else "Não especificado"
                
                salvar_no_historico("RH", cargo, nota or 0, resultado[:200] + "...")
                st.success("✅ Análise salva no histórico do sistema!")

# --- DASHBOARD DE HISTÓRICO ---
if st.session_state.get("mostrar_historico", False):
    st.divider()
    st.header("📊 Dashboard de Evolução e Histórico")
    
    df = pd.read_sql_query("SELECT data, modo, cargo, nota, resumo_feedback FROM historico ORDER BY id DESC", conn)
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Sessões", len(df))
        col2.metric("Média de Notas", f"{df['nota'].mean():.1f}" if df['nota'].mean() else "N/A")
        col3.metric("Modo Mais Usado", df['modo'].value_counts().idxmax())
        
        st.subheader("Últimas Análises")
        st.dataframe(df[['data', 'modo', 'cargo', 'nota']], use_container_width=True)
        
        # Gráfico de evolução de notas
        st.line_chart(df.set_index('data')['nota'])
        
        if st.button("Fechar Histórico"):
            st.session_state.mostrar_historico = False
            st.rerun()
    else:
        st.info("Nenhum registro encontrado ainda. Realize uma entrevista ou análise para ver os dados aqui.")
