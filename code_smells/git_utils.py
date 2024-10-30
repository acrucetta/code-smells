import subprocess
from typing import List, Dict

def run_git_command(command: str) -> str:
    """Run a git command and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            check=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {e.stderr}")

def get_current_branch() -> str:
    """Get the name of the current git branch."""
    return run_git_command("git branch --show-current")

def get_repo_name() -> str:
    """Get the name of the git repository."""
    return run_git_command("basename `git rev-parse --show-toplevel`")

def get_full_file_content(filename: str, branch: str) -> str:
    """Get the full content of a file from a specific branch."""
    try:
        return run_git_command(f"git show {branch}:{filename}")
    except:
        return ""
    
def get_staged_changes() -> str:
    """Get the staged changes from git."""
    try:
        return subprocess.check_output(
            ['git', 'diff', '--cached', '--unified=1'],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except:
        return ""

def get_diff(current_branch: str, compare_branch: str) -> str:
    """Get diff with file context between two branches."""
    # Get list of changed files
    changed_files = run_git_command(f"git diff --name-status {compare_branch}...{current_branch}").splitlines()
    
    output = []
    
    # Process each changed file
    for change in changed_files:
        status, filename = change.split(maxsplit=1)
        
        output.append(f"\n=== File: {filename} ===")
        output.append(f"Status: {status}")
        
        # if status != 'D':  # If file wasn't deleted
        #     output.append("\n=== Current File Content ===")
        #     output.append(get_full_file_content(filename, current_branch))
            
        output.append("\n=== Changes ===")
        # Get word-diff for this specific file
        try:
            file_diff = run_git_command(
                f"git diff --word-diff=plain {compare_branch}...{current_branch} -- {filename}"
            )
            output.append(file_diff)
        except:
            output.append("(New file or binary file)")
        
        output.append("\n" + "="*50)
    
    return "\n".join(output)