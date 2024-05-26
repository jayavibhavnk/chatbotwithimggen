import os
import requests
import tempfile
import shutil
import streamlit as st

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

from openai import OpenAI
client = OpenAI()
# Function to query OpenAI

def query_openai(query):
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": query}
    ],
    n = 1
    )

    return(completion.choices[0].message.content)

# Main function to run the script
def main():
    st.title("GitHub Repository Downloader")
    
    owner = st.text_input("GitHub Username", "your_github_username")
    repo = st.text_input("Repository Name", "your_repository_name")
    save_temp = st.checkbox("Save Temporarily", True)
    
    if st.button("Download Repository"):
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

if __name__ == "__main__":
    main()
