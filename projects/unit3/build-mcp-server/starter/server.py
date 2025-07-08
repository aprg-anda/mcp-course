#!/usr/bin/env python3
"""
Module 1: Basic MCP Server - Starter Code
TODO: Implement tools for analyzing git changes and suggesting PR templates
"""

import json
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("pr-agent")

# PR template directory (shared across all modules)
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


# TODO: Implement tool functions here
# Example structure for a tool:
# @mcp.tool()
# async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True) -> str:
#     """Get the full diff and list of changed files in the current git repository.
#     
#     Args:
#         base_branch: Base branch to compare against (default: main)
#         include_diff: Include the full diff content (default: true)
#     """
#     # Your implementation here
#     pass

# Minimal stub implementations so the server runs
# TODO: Replace these with your actual implementations

@mcp.tool()
async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True) -> str:
    """Get the full diff and list of changed files in the current git repository.
    
    Args:
        base_branch: Base branch to compare against (default: main)
        include_diff: Include the full diff content (default: true)
    """
    try:
        # Note: This runs git in the server's CWD.
        # For a real-world scenario, you'd want to get the project directory
        # from the MCP context as shown in the original stub comments.
        
        # Get changed files and statistics
        stat_command = ["git", "diff", "--stat", base_branch]
        stats_result = subprocess.run(stat_command, capture_output=True, text=True, check=True)
        
        # Get list of changed files
        files_command = ["git", "diff", "--name-only", base_branch]
        files_result = subprocess.run(files_command, capture_output=True, text=True, check=True)
        
        result = {
            "stats": stats_result.stdout.strip(),
            "changed_files": files_result.stdout.strip().splitlines(),
            "diff": None
        }

        if include_diff:
            diff_command = ["git", "diff", base_branch]
            diff_result = subprocess.run(diff_command, capture_output=True, text=True, check=True)
            # Limit diff size to avoid hitting response limits
            if len(diff_result.stdout) > 20000:
                result["diff"] = diff_result.stdout[:20000] + "\n... (diff truncated)"
            else:
                result["diff"] = diff_result.stdout
            
        return json.dumps(result, indent=2)
        
    except FileNotFoundError:
        return json.dumps({"error": "Git not found. Make sure it's installed and in your PATH."})
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "error": "An error occurred while running git.",
            "command": " ".join(e.cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
        })


@mcp.tool()
async def get_pr_templates() -> str:
    """List available PR templates with their content."""
    templates = []
    if not TEMPLATES_DIR.is_dir():
        return json.dumps({"error": f"Templates directory not found: {TEMPLATES_DIR}"})
        
    for template_file in TEMPLATES_DIR.glob("*.md"):
        try:
            content = template_file.read_text(encoding="utf-8")
            templates.append({"name": template_file.name, "content": content})
        except Exception as e:
            templates.append({"name": template_file.name, "error": f"Error reading template: {e}"})
            
    if not templates:
        return json.dumps({"warning": "No templates found.", "path": str(TEMPLATES_DIR)})

    return json.dumps(templates, indent=2)


@mcp.tool()
async def suggest_template(changes_summary: str, change_type: str) -> str:
    """Let Claude analyze the changes and suggest the most appropriate PR template.
    
    Args:
        changes_summary: Your analysis of what the changes do
        change_type: The type of change you've identified (bug, feature, docs, refactor, test, etc.)
    """
    potential_template_name = f"{change_type.lower()}.md"
    template_path = TEMPLATES_DIR / potential_template_name
    
    if template_path.is_file():
        try:
            content = template_path.read_text(encoding="utf-8")
            return json.dumps({
                "suggestion": potential_template_name,
                "content": content,
                "reason": f"The change type '{change_type}' directly maps to the '{potential_template_name}' template."
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error reading template '{potential_template_name}': {e}"})
    
    # Fallback to generic template
    generic_template_path = TEMPLATES_DIR / "generic.md"
    if generic_template_path.is_file():
        try:
            content = generic_template_path.read_text(encoding="utf-8")
            return json.dumps({
                "suggestion": "generic.md",
                "content": content,
                "reason": f"No specific template for '{change_type}' found. Falling back to 'generic.md'."
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error reading generic template: {e}"})

    return json.dumps({
        "error": f"No suitable template found for change type '{change_type}'.",
        "hint": f"Consider creating a template named '{change_type.lower()}.md' or 'generic.md' in {TEMPLATES_DIR}."
    })


if __name__ == "__main__":
    mcp.run()