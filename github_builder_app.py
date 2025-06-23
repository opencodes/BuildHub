import os
import shutil
import zipfile
from pathlib import Path
from git import Repo, GitCommandError
import streamlit as st

# Workspace to store cloned repos and builds
WORKSPACE_DIR = Path("workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)

# Default folders for each project type
BUILD_DIRS = {
    "UI": ["build", "dist", "out"],
    "Microservice": ["target", "app", "output"]
}

# Clone the repo from the given URL and branch


def clone_repo(repo_url, dest_path, branch="main"):
    if dest_path.exists():
        shutil.rmtree(dest_path)
    Repo.clone_from(repo_url, dest_path, branch=branch)

# Fetch all remote branches from a repo


def get_branches(repo_url):
    tmp_path = WORKSPACE_DIR / "temp_repo"
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    repo = Repo.clone_from(repo_url, tmp_path, depth=1)
    branches = [ref.name.split('/')[-1] for ref in repo.remote().refs]
    shutil.rmtree(tmp_path)
    return sorted(set(branches))

# Zip the given directory


def zip_directory(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)

# Search for build folder based on project type


def find_build_dir(repo_path, project_type):
    for folder in BUILD_DIRS[project_type]:
        candidate = repo_path / folder
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None

# Streamlit UI


def main():
    st.set_page_config(
        page_title="GitHub UI/Microservice Builder", layout="centered")
    st.title("🛠️ GitHub UI/Microservice Builder")

    # --- Session state ---
    if "branches" not in st.session_state:
        st.session_state.branches = []

    if "selected_branch" not in st.session_state:
        st.session_state.selected_branch = None

    # --- UI Inputs ---
    repo_url = st.text_input(
        "🔗 GitHub repo URL", placeholder="https://github.com/user/repo")

    if repo_url and st.button("🔄 Fetch Branches"):
        try:
            with st.spinner("Fetching branches..."):
                branches = get_branches(repo_url)
            st.session_state.branches = branches
            st.success("Branches fetched.")
        except GitCommandError as e:
            st.error(f"Failed to fetch branches: {e}")

    if st.session_state.branches:
        selected_branch = st.selectbox(
            "🌿 Select Branch", st.session_state.branches)
        st.session_state.selected_branch = selected_branch
    else:
        selected_branch = None

    project_type = st.selectbox(
        "📦 Select Project Type", ["UI", "Microservice"])

    # --- Build ---
    if st.button("🚀 Build & Package"):
        if not repo_url or not st.session_state.selected_branch:
            st.warning("❗ Please provide a GitHub URL and select a branch.")
            return

        branch = st.session_state.selected_branch
        repo_name = repo_url.rstrip('/').split('/')[-1]
        repo_path = WORKSPACE_DIR / f"{repo_name}-{branch}"

        try:
            st.info(f"Cloning `{branch}`...")
            clone_repo(repo_url, repo_path, branch)
            st.success("✅ Repository cloned.")
        except Exception as e:
            st.error(f"❌ Error cloning repo: {e}")
            return

        st.info(f"🔍 Searching for build folder for {project_type}...")
        build_path = find_build_dir(repo_path, project_type)

        if not build_path:
            st.error(
                f"❌ No build folder found for {project_type}. Expected one of: {', '.join(BUILD_DIRS[project_type])}")
            return

        zip_filename = f"{repo_name}-{branch}-{project_type}.zip"
        zip_path = WORKSPACE_DIR / zip_filename
        zip_directory(build_path, zip_path)
        st.success(f"📦 Packaged from `{build_path}`")

        with open(zip_path, "rb") as file:
            st.download_button("📥 Download ZIP", file, file_name=zip_filename)


if __name__ == "__main__":
    main()
