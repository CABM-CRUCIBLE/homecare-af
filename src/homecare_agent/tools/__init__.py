# Author: C A B M
# Date: 2026-09-17

"""Tools package for the HomeCare Agentic Framework."""

from homecare_agent.tools.build_tools import (
    BuildResult,
    TestResult,
    dotnet_build,
    dotnet_test,
    npm_build,
    npm_lint,
    npm_test,
)
from homecare_agent.tools.codebase_tools import (
    analyze_controllers,
    analyze_entities,
    analyze_frontend_routes,
    analyze_solution,
    find_related_features,
    get_dependency_graph,
)
from homecare_agent.tools.file_tools import (
    delete_file,
    extract_files_from_markdown,
    list_files,
    read_file,
    write_file,
)
from homecare_agent.tools.git_tools import (
    get_current_branch,
    git_add,
    git_checkout,
    git_commit,
    git_diff,
    git_push,
    git_status,
)
from homecare_agent.tools.github_tools import (
    add_review_comment,
    create_pull_request,
    get_pr_diff,
    post_pr_review,
)
from homecare_agent.tools.image_tools import (
    analyze_wireframe,
    encode_image_to_base64,
    get_image_data_uri,
    get_image_metadata,
)
from homecare_agent.tools.mermaid_tools import (
    generate_er_diagram,
    generate_flowchart,
    generate_sequence_diagram,
    validate_mermaid_syntax,
)

__all__ = [
    # Build
    "dotnet_build",
    "dotnet_test",
    "npm_build",
    "npm_test",
    "npm_lint",
    "BuildResult",
    "TestResult",
    # Codebase
    "analyze_solution",
    "analyze_entities",
    "analyze_controllers",
    "analyze_frontend_routes",
    "find_related_features",
    "get_dependency_graph",
    # File
    "read_file",
    "write_file",
    "delete_file",
    "list_files",
    "extract_files_from_markdown",
    # Git
    "git_checkout",
    "git_add",
    "git_commit",
    "git_push",
    "git_status",
    "git_diff",
    "get_current_branch",
    # GitHub
    "create_pull_request",
    "get_pr_diff",
    "add_review_comment",
    "post_pr_review",
    # Image
    "get_image_metadata",
    "encode_image_to_base64",
    "get_image_data_uri",
    "analyze_wireframe",
    # Mermaid
    "generate_er_diagram",
    "generate_sequence_diagram",
    "generate_flowchart",
    "validate_mermaid_syntax",
]
