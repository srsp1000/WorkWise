"""
WorkWise Frontend Packaging Script
Creates a POSIX-compliant ZIP archive of the `frontend/dist` directory.
Ensures forward slashes (/) are preserved for AWS Amplify & Linux S3 compatibility.
"""
import os
import zipfile

def package_frontend():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(repo_root, "frontend", "dist")
    zip_path = os.path.join(repo_root, "frontend", "dist.zip")

    if not os.path.exists(dist_dir):
        raise FileNotFoundError(f"Directory not found: {dist_dir}. Run 'npm run build' first.")

    print(f"Creating POSIX ZIP from: {dist_dir}")
    print(f"Destination archive:     {zip_path}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dist_dir)
                # Ensure POSIX forward slashes regardless of host OS (Windows/Mac/Linux)
                posix_path = rel_path.replace(os.sep, "/")
                zf.write(full_path, arcname=posix_path)
                print(f"  + Added: {posix_path}")

    print("\n[SUCCESS] dist.zip successfully created with forward slash paths.")

if __name__ == "__main__":
    package_frontend()
