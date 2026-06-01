import os
import shutil
from git import Repo
from pathlib import Path

# Directories and explicit file extensions to slice out of our indexing space
IGNORED_FOLDERS = {
    'node_modules', '.git', 'build', 'dist', 'bin', 'obj', 
    'venv', 'env', '__pycache__', 'target', '.next', '.vercel'
}

IGNORED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp3', '.mp4',
    '.pdf', '.zip', '.tar', '.gz', '.lock', '-lock.json', '.yaml', '.yml',
    '.woff', '.woff2', '.eot', '.ttf', '.exe', '.dll', '.so', '.dylib'
}

class RepositoryManager:
    def __init__(self, base_download_dir="tmp_repos"):
        # Store temporary clones inside the workspace directory for easy relative tracking
        self.base_dir = Path(__file__).parent / base_download_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def extract_source_files(self, repo_path):
        """Walks the repository and structural profiles code files for indexing."""
        valid_files = []
        repo_path_obj = Path(repo_path)

        for root, dirs, files in os.walk(str(repo_path_obj)):
            # Modifying dirs in-place tells os.walk to completely skip walking into ignored paths
            dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

            for file in files:
                file_path = Path(root) / file
                
                # Verify structural file constraints
                if file_path.suffix.lower() in IGNORED_EXTENSIONS:
                    continue
                if file.endswith('lock.json') or file.endswith('.lock'):
                    continue

                try:
                    # Attempt reading contents; binary blobs throw errors or contain zero-bytes
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Calculate clean relative paths for frontend tree views
                    relative_path = file_path.relative_to(repo_path_obj)
                    
                    valid_files.append({
                        "relative_path": str(relative_path).replace("\\", "/"),
                        "absolute_path": str(file_path),
                        "extension": file_path.suffix,
                        "content": content
                    })
                except (UnicodeDecodeError, ValueError):
                    # Gracefully skip any binary compiled files that passed extension checks
                    continue

        print(f"✅ Code cleaning filter complete. Found {len(valid_files)} valid source files.")
        return valid_files

    def _remove_readonly(self, func, path, excinfo):
        """Helper to force file attributes to writable so Windows allows deletion."""
        os.chmod(path, 0o777)
        func(path)

    def clone_repo(self, repo_url, repo_id):
        """Sanitizes arguments and clones a remote repository to a local folder."""
        # FIX: Force-strip hidden whitespaces or trailing spaces from incoming request text strings
        sanitized_url = str(repo_url).strip()
        sanitized_id = str(repo_id).strip()

        # Build clean Path object away from Windows syntax limits
        target_path = self.base_dir / sanitized_id
        
        # Clean up existing duplicate folder path using our Windows-safe handler
        if target_path.exists():
            print(f"🧹 Found older tracking folder data for {sanitized_id}. Purging files safely...")
            shutil.rmtree(target_path, onerror=self._remove_readonly)
            
        print(f"📥 Cloning target repository: {sanitized_url} into storage...")
        # Passing an absolute path string ensures GitPython maps perfectly onto the shell
        Repo.clone_from(sanitized_url, str(target_path.resolve()), depth=1)
        return target_path

    def cleanup(self, repo_path):
        """Removes the cloned repository directory workspace once parsed."""
        if repo_path:
            try:
                # Convert path types to a unified path layout string representation
                path_to_remove = str(Path(repo_path).resolve())
                if os.path.exists(path_to_remove):
                    shutil.rmtree(path_to_remove, onerror=self._remove_readonly)
                    print(f"🧹 Cleaned up temporary ingestion directory: {path_to_remove}")
            except Exception as e:
                print(f"⚠️ Minor warning during cleanup: {str(e)}")