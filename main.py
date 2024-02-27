import streamlit as st
import time
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from PIL import Image
from io import BytesIO

# OPENAI_API_KEY = st.secrets.OPENAI_API_KEY

st.set_page_config(
        page_title="Chatbor Name here",
        page_icon="✍️",
        # layout="wide",
        initial_sidebar_state="expanded",
    )

st.sidebar.title("Customization Options")

customization_options = {
        "Generation_type": st.sidebar.radio("Generation Type", ["Text", "Image"])
    }


st.title("💬 yo yo chatbot")

llm = ChatOpenAI(temperature=0.9, openai_api_key = OPENAI_API_KEY)

def get_image_from_api(text):
    # Replace with your API function call
    import requests

    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": "Bearer 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"}

    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.content
    image_bytes = query({
        "inputs": "{}".format(text),
    })

    return image_bytes

def query_openai(text):
    prompt = "{prompt}"
    prompt = ChatPromptTemplate.from_template(
        prompt
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    res = chain.run(prompt = text)

    return res

if customization_options['Generation_type'] == "Text":
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input():

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        msg = query_openai(prompt)

        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)

if customization_options['Generation_type'] == "Image":
    try:
        st.write("Enter Image Generation Prompt:")
        prompt = st.text_input("Prompt: ")
        if prompt:
            with st.spinner("Generating Image..."):
                img = get_image_from_api(prompt)
                # st.write("Generated Image:")
                # print(img)
                if img:
                    image = Image.open(BytesIO(img))
                    st.image(image, caption="Generated Image", use_column_width=True)
    except:
        pass

