import os
import requests
import tempfile
import shutil
import streamlit as st
import openai
import nbformat
from GraphRetrieval import GraphRAG

from openai import OpenAI
client = OpenAI()

# Function to get the contents of a repository
def get_repo_contents(owner, repo, path="", token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure we notice bad responses
    return response.json()

# Function to download a file from GitHub and return its content
def download_file(owner, repo, file_path, branch="main", save_dir=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure we notice bad responses
    
    content = response.content
    
    if save_dir:
        # Create local directories if they don't exist
        os.makedirs(os.path.dirname(os.path.join(save_dir, file_path)), exist_ok=True)
        with open(os.path.join(save_dir, file_path), 'wb') as file:
            file.write(content)
    
    return content.decode('utf-8')

# Function to recursively download all files in a repository and return their content
def download_repo(owner, repo, save_dir=None, path="", branch="main", token=None):
    contents = get_repo_contents(owner, repo, path, token)
    all_files_content = ""
    for item in contents:
        if item['type'] == 'file':
            file_content = download_file(owner, repo, item['path'], branch, save_dir, token)
            all_files_content += file_content + "\n"
        elif item['type'] == 'dir':
            all_files_content += download_repo(owner, repo, save_dir, item['path'], branch, token)
    
    return all_files_content

# Function to query OpenAI with exception handling
def query_openai(query):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": query}
            ],
            n=1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return str(e)

# Function to convert Jupyter notebook to plain text
def notebook_to_text(nb):
    cells = nb['cells']
    text = ''
    for cell in cells:
        if cell['cell_type'] == 'code':
            text += ''.join(cell['source']) + '\n'
    return text

# Main function to run the script
def main():
    st.title("GRAEL - Code Explainer!!")

    if "repo_content" not in st.session_state:
        st.session_state.repo_content = ""
    if "file_content" not in st.session_state:
        st.session_state.file_content = ""
    if "explanation" not in st.session_state:
        st.session_state.explanation = ""
    if "graph_created" not in st.session_state:
        st.session_state.graph_created = False
    if "owner" not in st.session_state:
        st.session_state.owner = ""
    if "repo" not in st.session_state:
        st.session_state.repo = ""
    if "branch" not in st.session_state:
        st.session_state.branch = "main"
    if "token" not in st.session_state:
        st.session_state.token = ""
    if "save_temp" not in st.session_state:
        st.session_state.save_temp = True

    option = st.selectbox(
        "Choose an option",
        ("Download GitHub Repository", "Upload Files for Explanation")
    )
    
    if option == "Download GitHub Repository":
        st.header("Download GitHub Repository")
        st.session_state.owner = st.text_input("GitHub Username", st.session_state.owner)
        st.session_state.repo = st.text_input("Repository Name", st.session_state.repo)
        st.session_state.branch = st.text_input("Branch (default is 'main')", st.session_state.branch)
        st.session_state.token = st.secrets['github_pat'] # st.text_input("GitHub Personal Access Token (optional)", type="password")
        st.session_state.save_temp = st.checkbox("Save Temporarily", st.session_state.save_temp)
        
        if st.button("Explain Repository"):
            if st.session_state.owner and st.session_state.repo:
                try:
                    if st.session_state.save_temp:
                        # Create a temporary directory
                        with tempfile.TemporaryDirectory() as temp_dir:
                            st.session_state.repo_content = download_repo(
                                st.session_state.owner, st.session_state.repo, temp_dir, branch=st.session_state.branch, token=st.session_state.token
                            )
                            st.write(f"Repository downloaded temporarily at {temp_dir}")
                            # Provide a link to download the files as a zip
                            shutil.make_archive(temp_dir, 'zip', temp_dir)
                            with open(f"{temp_dir}.zip", "rb") as f:
                                st.download_button("Download ZIP", f, file_name=f"{st.session_state.repo}.zip")
                            st.text_area("All Files Content", st.session_state.repo_content, height=300)
                    else:
                        save_dir = st.text_input("Save Directory", "path_to_save_directory")
                        st.session_state.repo_content = download_repo(
                            st.session_state.owner, st.session_state.repo, save_dir, branch=st.session_state.branch, token=st.session_state.token
                        )
                        st.write(f"Repository downloaded at {save_dir}")
                        st.text_area("All Files Content", st.session_state.repo_content, height=300)
                    
                    # Get explanation from OpenAI
                    explanation_query = "give me the explanation of this code as a markdown You will always start with The project title and do not use phrases such as here is your code explanation"
                    st.session_state.explanation = query_openai(explanation_query + "\n\n" + st.session_state.repo_content[:16000])
                    
                    st.markdown(st.session_state.explanation)
                    
                    # Create graph from downloaded content as text using GraphRAG
                    grag = GraphRAG()
                    grag.create_graph_from_text(st.session_state.repo_content)

                    st.session_state.graph_created = True
                    st.write("Graph Created!")
                
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                
    elif option == "Upload Files for Explanation":
        st.header("Upload Files for Explanation")
        uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=["py", "ipynb"])
        
        if uploaded_files:
            all_files_content = ""
            for uploaded_file in uploaded_files:
                if uploaded_file.type == "application/x-ipynb+json":
                    # Parse Jupyter notebook
                    notebook = nbformat.read(uploaded_file, as_version=4)
                    file_content = notebook_to_text(notebook)
                else:
                    # Read Python script
                    file_content = uploaded_file.read().decode("utf-8")
                
                all_files_content += file_content + "\n"
            
            st.session_state.file_content = all_files_content

            # Display the content of the uploaded files
            st.text_area("Uploaded Files Content", st.session_state.file_content, height=300)
            
            # Get explanation from OpenAI
            explanation_query = "give me the explanation of this code as a markdown"
            st.session_state.explanation = query_openai(explanation_query + "\n\n" + st.session_state.file_content)
            
            st.markdown(st.session_state.explanation)
            
            # Create graph from uploaded content using GraphRAG
            grag = GraphRAG()
            grag.create_graph_from_text(st.session_state.file_content)
            
            st.session_state.graph_created = True

    if st.session_state.graph_created:
        # User query input box
        user_query = st.text_input("Ask a question about the code")
        if user_query:
            grag = GraphRAG()  # Create a new instance to avoid any issues
            grag.create_graph_from_text(st.session_state.repo_content + st.session_state.file_content)
            response = grag.queryLLM(user_query)
            st.write(response)

if __name__ == "__main__":
    main()
