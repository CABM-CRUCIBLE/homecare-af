# Author: C A B M
# Date: 2026-09-17

"""Unit tests for HomeCare Agentic Framework tools."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from homecare_agent.tools.build_tools import BuildResult, TestResult

TestResult.__test__ = False
from homecare_agent.tools.file_tools import (
    delete_file,
    extract_files_from_markdown,
    list_files,
    read_file,
    write_file,
)
from homecare_agent.tools.github_tools import _clean_repo_name
from homecare_agent.tools.mermaid_tools import (
    generate_er_diagram,
    generate_flowchart,
    generate_sequence_diagram,
    validate_mermaid_syntax,
)


def test_file_tools_read_write_delete(tmp_path: Path):
    test_file = tmp_path / "sub" / "test.txt"
    content = "Hello, HomeCare Enterprise!"

    # Write
    written_path = write_file(test_file, content)
    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8") == content

    # Read
    read_back = read_file(test_file)
    assert read_back == content

    # List
    files = list_files(tmp_path, "*.txt")
    assert len(files) == 1
    assert files[0] == test_file

    # Delete
    deleted = delete_file(test_file)
    assert deleted is True
    assert not test_file.exists()


def test_extract_files_from_markdown():
    sample_markdown = """\
Here is the implementation:

```csharp filepath="code/backend/Domain/Entities/Order.cs"
namespace HomeCare.Domain.Entities;
public class Order { public Guid Id { get; set; } }
```

And the frontend component:

### `code/frontend/components/OrderList.tsx`
```tsx
export function OrderList() { return <div>Orders</div>; }
```
"""
    files = extract_files_from_markdown(sample_markdown)
    assert "code/backend/Domain/Entities/Order.cs" in files
    assert "namespace HomeCare.Domain.Entities;" in files["code/backend/Domain/Entities/Order.cs"]
    assert "code/frontend/components/OrderList.tsx" in files
    assert "OrderList" in files["code/frontend/components/OrderList.tsx"]


def test_mermaid_tools_er_diagram():
    entities = [
        {
            "name": "Patient",
            "attributes": [
                {"type": "uuid", "name": "Id"},
                {"type": "string", "name": "Name"},
            ],
        },
        {
            "name": "Order",
            "attributes": [
                {"type": "uuid", "name": "Id"},
                {"type": "uuid", "name": "PatientId"},
            ],
        },
    ]
    relationships = [
        {"from": "Patient", "to": "Order", "cardinality": "||--o{", "label": "places"}
    ]

    diagram = generate_er_diagram(entities, relationships)
    assert diagram.startswith("erDiagram")
    assert "Patient" in diagram
    assert "Order" in diagram

    valid, msg = validate_mermaid_syntax(diagram)
    assert valid is True


def test_mermaid_tools_sequence_diagram():
    participants = ["Client", "BFF", "Api"]
    interactions = [
        {"from": "Client", "to": "BFF", "message": "POST /api/orders"},
        {"from": "BFF", "to": "Api", "message": "Dispatch Order"},
        {"from": "Api", "to": "Client", "message": "Order Created", "type": "return"},
    ]

    diagram = generate_sequence_diagram(participants, interactions)
    assert "sequenceDiagram" in diagram
    assert "participant Client" in diagram
    valid, msg = validate_mermaid_syntax(diagram)
    assert valid is True


def test_mermaid_syntax_validation():
    # Valid flowchart
    valid, msg = validate_mermaid_syntax("flowchart TD\n  A --> B")
    assert valid is True

    # Invalid header
    valid, msg = validate_mermaid_syntax("unknownDiagram\n  A --> B")
    assert valid is False

    # Unbalanced braces
    valid, msg = validate_mermaid_syntax("erDiagram\n  Order {\n    uuid Id")
    assert valid is False


def test_clean_repo_name():
    assert _clean_repo_name("https://github.com/myorg/myrepo.git") == "myorg/myrepo"
    assert _clean_repo_name("https://github.com/myorg/myrepo") == "myorg/myrepo"
    assert _clean_repo_name("myorg/myrepo") == "myorg/myrepo"


def test_build_and_test_result_dataclasses():
    br = BuildResult(success=True, output="Build succeeded", errors="", return_code=0)
    assert br.success is True

    tr = TestResult(success=True, output="Passed", passed=10, failed=0, skipped=0, return_code=0)
    assert tr.passed == 10
