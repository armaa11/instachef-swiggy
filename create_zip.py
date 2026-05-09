import os
import zipfile

def create_zip():
    source_dir = 'mise-en-place'
    output_filename = 'mise-en-place.zip'
    
    exclusions = [
        'frontend/.next',
        'frontend/node_modules',
        'backend/venv',
        'backend/__pycache__',
        '__pycache__',
        '.git'
    ]
    
    def should_exclude(file_path):
        # convert to forward slashes for matching
        file_path = file_path.replace('\\', '/')
        if file_path.endswith('.env'):
            return True
        for excl in exclusions:
            if excl in file_path:
                return True
        return False

    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if not should_exclude(file_path):
                    # Keep structure inside zip, but optionally under mise-en-place folder
                    # The plan says: Option A: `mise-en-place.zip` at `swiggy-build/mise-en-place.zip` (recommended)
                    # and "contains frontend/ and backend/ at zip root"
                    
                    # Compute arcname to be relative to the source_dir
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")

if __name__ == '__main__':
    create_zip()
