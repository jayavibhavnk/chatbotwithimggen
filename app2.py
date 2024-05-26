import os
import requests
import tempfile
import shutil
import streamlit as st
import openai
import nbformat
from GraphRetrieval import GraphRAG

# Initialize OpenAI client
from openai import OpenAI
client = OpenAI()

# Function to get the contents of a repository
def get_repo_contents(owner, repo, path=""):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    return response.json()

# Function to download a file from GitHub and return its content
def download_file(owner, repo, file_path, save_dir=None):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{file_path}"
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    
    content = response.content
    
    if save_dir:
        # Create local directories if they don't exist
        os.makedirs(os.path.dirname(os.path.join(save_dir, file_path)), exist_ok=True)
        with open(os.path.join(save_dir, file_path), 'wb') as file:
            file.write(content)
    
    return content.decode('utf-8')

# Function to recursively download all files in a repository and return their content
def download_repo(owner, repo, save_dir=None, path=""):
    contents = get_repo_contents(owner, repo, path)
    all_files_content = ""
    for item in contents:
        if item['type'] == 'file':
            file_content = download_file(owner, repo, item['path'], save_dir)
            all_files_content += file_content + "\n"
        elif item['type'] == 'dir':
            all_files_content += download_repo(owner, repo, save_dir, item['path'])
    
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
        return completion.choices[0].message['content']
    except Exception as e:
        return f"An error occurred: {str(e)}"

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
    st.title("Code Downloader and Explainer")

    option = st.selectbox(
        "Choose an option",
        ("Download GitHub Repository", "Upload Files for Explanation")
    )
    
    if option == "Download GitHub Repository":
        st.header("Download GitHub Repository")
        owner = st.text_input("GitHub Username", "your_github_username")
        repo = st.text_input("Repository Name", "your_repository_name")
        save_temp = st.checkbox("Save Temporarily", True)
        
        if st.button("Download Repository"):
            if owner and repo:
                if save_temp:
                    # Create a temporary directory
                    with tempfile.TemporaryDirectory() as temp_dir:
                        all_files_content = download_repo(owner, repo, temp_dir)
                        st.write(f"Repository downloaded temporarily at {temp_dir}")
                        # Provide a link to download the files as a zip
                        shutil.make_archive(temp_dir, 'zip', temp_dir)
                        with open(f"{temp_dir}.zip", "rb") as f:
                            st.download_button("Download ZIP", f, file_name=f"{repo}.zip")
                        st.text_area("All Files Content", all_files_content, height=300)
                else:
                    save_dir = st.text_input("Save Directory", "path_to_save_directory")
                    all_files_content = download_repo(owner, repo, save_dir)
                    st.write(f"Repository downloaded at {save_dir}")
                    st.text_area("All Files Content", all_files_content, height=300)
                
                # Get explanation from OpenAI
                explanation_query = "give me the explanation of this code as a markdown"
                explanation = query_openai(explanation_query + "\n\n" + all_files_content)
                
                st.markdown(explanation)
                
                # Create graph from downloaded content using GraphRAG
                grag = GraphRAG()
                if save_temp:
                    grag.create_graph_from_directory(temp_dir)
                else:
                    grag.create_graph_from_directory(save_dir)
                
                # User query input box
                user_query = st.text_input("Ask a question about the code")
                if user_query:
                    response = grag.queryLLM(user_query)
                    st.write(response)
                
            else:
                st.error("Please enter both GitHub username and repository name.")
    
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
            
            # Display the content of the uploaded files
            st.text_area("Uploaded Files Content", all_files_content, height=300)
            
            # Get explanation from OpenAI
            explanation_query = "give me the explanation of this code as a markdown"
            explanation = query_openai(explanation_query + "\n\n" + all_files_content)
            
            st.markdown(explanation)
            
            # Create graph from uploaded content using GraphRAG
            grag = GraphRAG()
            grag.create_graph_from_text(all_files_content)
            
            # User query input box
            user_query = st.text_input("Ask a question about the code")
            if user_query:
                response = grag.queryLLM(user_query)
                st.write(response)

if __name__ == "__main__":
    main()
