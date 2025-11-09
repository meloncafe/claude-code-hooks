# Claude Skills Practical Template Collection

## Table of Contents

1. [Basic Skill Template](#basic-skill-template)
2. [Progressive Disclosure Example](#progressive-disclosure-example)
3. [Workflow Example](#workflow-example)
4. [Code Inclusion Example](#code-inclusion-example)
5. [Domain-Specific Examples](#domain-specific-examples)

---

## Basic Skill Templates

### Template 1: Simple Skill (Single File)

```markdown
---
name: simple-task
description: [What it does]. Use when [When to use it].
---

# Simple Task

## Quick start

[Minimal example for the most common use case]

```python
# Core code
```

## Common variations

**Case 1**: [Description] → [Solution]
**Case 2**: [Description] → [Solution]

## Troubleshooting

**Error X**: [Cause] → [Solution]
**Error Y**: [Cause] → [Solution]
```

**Example Usage**:
```markdown
---
name: json-validation
description: Validate and format JSON files, fixing common syntax errors. Use when working with JSON files or when user mentions JSON validation, formatting, or syntax errors.
---

# JSON Validation

## Quick start

Basic Validation:

```python
import json

with open(‘data.json’) as f:
    try:
        data = json.load(f)
        print(“✓ Valid JSON”)
    except json.JSONDecodeError as e:
        print(f“✗ Error at line {e.lineno}: {e.msg}”)
```

## Common Issues

**Trailing commas**: Not allowed in JSON → Remove last comma
**Single quotes**: Not allowed → Change to double quotes
**Unquoted keys**: Not allowed → Enclose keys in quotes

## Automatic Fixing

```python
import json5  # Install JSON5 parser: pip install json5

with open(‘broken.json’) as f:
    data = json5.load(f)  # Allows loose syntax

# Save as standard JSON
with open(‘fixed.json’, ‘w’) as f:
    json.dump (data, f, indent=2)
```
```

---

## Progressive Disclosure Example

### Example 1: Document Processing Skill

**Directory Structure**:
```
docx-skill/
├── SKILL.md                    # Main guide (always loaded)
├── ADVANCED.md                 # Advanced features (if needed)
├── REDLINING.md                # Tracked changes (if needed)
├── OOXML.md                    # Technical reference (if needed)
└── scripts/
    ├── validate.py             # Validation script
    └── pack.py                 # Packing script
```

**SKILL.md** (Main):
```markdown
---
name: docx-processing
description: Create and edit Word documents (.docx), including tracked changes and comments. Use when working with Word documents or when user mentions .docx, document editing, or tracked changes.
---

# DOCX Processing

## Creating a New Document

Using python-docx:

```python
from docx import Document

doc = Document()
doc.add_heading(‘Document Title’, 0)
doc.add_paragraph(‘Hello World’)
doc.save(‘output.docx’)
```

## Editing an Existing Document

For simple text changes using python-docx:
```python
doc = Document(‘existing.docx’)
doc.paragraphs[0].text = ‘New text’
doc.save(‘modified.docx’)
```

**For complex editing needs**:
- **Track Changes**: See [REDLINING.md](REDLINING.md)
- **Advanced Formatting**: See [ADVANCED.md](ADVANCED.md)
- **OOXML Modifications**: See [OOXML.md](OOXML.md)

## Document Validation

Always validate after editing:
```bash
python scripts/validate.py document.docx
```
```

**REDLINING.md** (Load if needed):
```markdown
# Track Changes Guide

## Overview

Word's Track Changes feature is implemented using OOXML's `<w:ins>` and `<w:del>` tags.

## Workflow

1. **Unzip Document**:
   ```bash
   unzip document.docx -d unpacked/
   ```

2. **Edit XML**:
   ```xml
   <!-- Insert text -->
   <w:ins w:id=“1” w:author=‘Claude’ w:date=“2025-10-28T00:00:00Z”>
     <w:r><w:t>New text</w:t></w:r>
   </w:ins>   <!-- Text deletion -->
   <w:del w:id=“2” w:author=‘Claude’ w:date=“2025-10-28T00:00:00Z”>
     <w:r><w:delText>Old text</w:delText></w:r>
   </w:del>
   ```

3. **Verification and Recompression**:
 ```bash
   python scripts/validate.py unpacked/
   python scripts/pack.py unpacked/ output.docx
   ```

## Full examples are available at [EXAMPLES.md](EXAMPLES.md)
```

---

### Example 2: Data Analysis Skill (Domain-Specific)

**Directory Structure**:
```
bigquery-skill/
├── SKILL.md                    # Overview and navigation
└── reference/
    ├── finance.md              # Finance schema
    ├── sales.md                # Sales schema
    ├── product.md              # Product schema
    └── marketing.md            # Marketing schema
```

**SKILL.md**:
```markdown
---
name: bigquery-analytics
description: Query and analyze company data from BigQuery across finance, sales, product, and marketing datasets. Use when analyzing business metrics, revenue, pipeline, or campaign data.
---

# BigQuery Analytics

## Available Datasets

| Domain | Key Metrics | Schema Reference |
|--------|-------------|-------------|
| **Finance** | Revenue, ARR, Billing | [reference/finance.md](reference/finance.md) |
| **Sales** | Opportunities, Pipeline | [reference/sales.md](reference/sales.md) |
| **Product** | API Usage, Features | [reference/product.md](reference/product.md) |
| **Marketing** | Campaigns, Conversions | [reference/marketing.md](reference/marketing.md) |

## Quick Search

Find specific metrics:

```bash
# Find tables related to revenue
grep -i “revenue” reference/finance.md

# Find tables related to pipeline
grep -i “pipeline” reference/sales.md
```

## Query Templates

**Monthly Revenue**:
```sql
SELECT
  DATE_TRUNC(date, MONTH) as month,
  SUM(amount) as revenue
FROM finance.transactions
GROUP BY month
ORDER BY month DESC
```

See the relevant domain reference file for detailed schema.
```

**reference/finance.md**:
```markdown
# Finance Data Schema

## finance.transactions

Monthly Transaction Data

| Column | Type | Description |
|------|------|------|
| transaction_id | STRING | Unique transaction ID |
| date | DATE | Transaction date |
| customer_id | STRING | Customer ID |
| amount | FLOAT64 | Transaction Amount (USD) |
| type | STRING | ‘revenue’, ‘refund’, ‘chargeback’ |
| subscription_id | STRING | Subscription ID (if applicable) |

## finance.arr

Annual Recurring Revenue

| Column | Type | Description |
|------|--| -----|------|
| date | DATE | Snapshot date |
| arr | FLOAT64 | Total ARR (USD) |
| new_arr | FLOAT64 | New ARR |
| expansion_arr | FLOAT64 | Expansion ARR |
| churn_arr | FLOAT64 | Churn ARR |

## Common Queries

**Quarterly ARR Growth**:
```sql
SELECT
  DATE_TRUNC(date, QUARTER) as quarter,
  MAX(arr) as ending_arr,
  SUM(new_arr) as total_new,
  SUM(expansion_arr) as total_expansion,
  SUM(churn_arr) as total_churn
FROM finance.arr
GROUP BY quarter
ORDER BY quarter DESC
```
```

---

## Workflow Examples

### Example 1: Checklist-Based Workflow

```markdown
---
name: code-review-workflow
description: Conduct thorough code reviews with a checklist-based approach. Use when reviewing code, pull requests, or when a user requests a code review.
---

# Code Review Workflow

## Review Process

Copy the checklist below and check each item:

```
Code Review Process:
- [ ] Step 1: Analyze code structure
- [ ] Step 2: Verify functional accuracy
- [ ] Step 3: Check edge cases
- [ ] Step 4: Review performance
- [ ] Step 5: Inspect security vulnerabilities
- [ ] Step 6: Verify test coverage
- [ ] Step 7: Review documentation
- [ ] Step 8: Compile comprehensive feedback
```

### Step 1: Code Structure Analysis

**Checkpoints**:
- [ ] Are function/class responsibilities clear?
- [ ] Is the abstraction level appropriate?
- [ ] Is naming consistent and clear?
- [ ] Is there duplicate code?

**Feedback Format**:
```
## Structure
✓ Clear separation of concerns
⚠ UserService has too many responsibilities → Suggest separation
```

### Step 2: Functional Accuracy Verification

**Checklist**:
- [ ] Have all requirements been implemented?
- [ ] Is the logic correct?
- [ ] Does it produce the correct output for expected inputs?

**Feedback Format**:
```
## Functionality
✓ Basic flow is correct
✗ Crashes on empty array input → Need to add null check
```

### Steps 3-8 follow a similar pattern...

## Final Report Template

```markdown
# Code Review: [PR Title]

## Summary
- **Status**: Approved / Requires Changes / Comments
- **Key Findings**: [One-sentence summary]

## Positive Aspects
- [What's Good 1]
- [Well-done point 2]

## Areas for Improvement
### 🔴 Critical (Must fix before merge)
- [Serious issue]

### 🟡 Important (Fix in next PR)
- [Important but non-blocking issue]

### 🟢 Nice to have (Optional)
- [Minor improvement suggestions]

## Detailed Comments
[Detailed feedback per file/function]
```
```

### Example 2: Feedback Loop Workflow

```markdown
---
name: api-integration-workflow
description: Integrate external APIs with validation and error handling workflow. Use when integrating third-party APIs or external services.
---

# API Integration Workflow

## Integration Process

### Phase 1: Verify Specifications

1. Read API documentation
2. Confirm authentication method (API key, OAuth, etc.)
3. Check rate limits
4. Verify test endpoints

**Validation**: Are the API documentation URL and authentication credentials ready?
- Yes → Proceed to Phase 2
- No → Collect documentation and restart

### Phase 2: Connection Test

```python
import requests

# Test request
response = requests.get(
    ‘https://api.example.com/health’,
    headers={‘Authorization’: f'Bearer {API_KEY}'}
)

print(f“Status: {response.status_code}”)
print(f“Response: {response.json()}”)
```

**Verification**: Did you receive a 200 response?
- Yes → Proceed to Phase 3
- No → Verify credentials and repeat Phase 2

### Phase 3: Core Functionality Implementation

```python
def get_data(endpoint, params=None):
    “”“Common API call function”“”    response = requests.get(
        f'{BASE_URL}/{endpoint}',
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

**Verification**: Can actual data be fetched?
- Yes → Proceed to Phase 4
- No → Check error logs and repeat Phase 3

### Phase 4: Error Handling

```python
from requests.exceptions import RequestException, Timeout

def safe_api_call(endpoint, params=None, retries=3):
    “”“Safe API call with retry logic”" “
    for attempt in range(retries):
        try:
            return get_data(endpoint, params)
        except Timeout:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
        except RequestException as e:
            logger.error(f”API error: {e}")
            raise
```

**Verification**: Is it handled appropriately when a network error occurs?
- Yes → Proceed to Phase 5
- No → Add error case and repeat Phase 4

### Phase 5: Write Tests

```python
def test_api_integration():
    # Normal case
    data = safe_api_call(‘users/123’)
    assert data[‘id’] == ‘123’    # Error case
    with pytest.raises(RequestException):
        safe_api_call(‘invalid/endpoint’)

    # Timeout
    with pytest.raises(Timeout):
        safe_api_call(‘slow/endpoint’)
```

**Verification**: Do all tests pass?
- Yes → Complete!
- No → Fix failed tests and repeat Phase 5
```

---

## Code-Included Examples

### Example 1: Including Utility Scripts

**Directory Structure**:
```
pdf-skill/
├── SKILL.md
├── FORMS.md
└── scripts/
    ├── analyze_form.py
    ├── validate_fields.py
    └── fill_form.py
```

**SKILL.md**:
```markdown
---
name: pdf-form-filling
description: Analyze and fill PDF forms programmatically. Use when working with PDF forms, field extraction, or form automation.
---

# PDF Form Filling

## Workflow

### Step 1: Analyze the Form

Extract form fields using the `analyze_form.py` script:

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

**Output Format**:
```json
{
  “applicant_name”: {
    “type”: “text”,
    “page”: 1,
    “x”: 100, “y”: 200,
    “width”: 200, “height”: 20
  },
  ‘signature’: {
    “type”: “signature”,
    “page”: 2,
    “x”: 150, “y”: 500,
    ‘width’: 300, “height”: 50
  }
}
```

### Step 2: Value Mapping

Edit `fields.json` to add values for each field:

```json
{
  “applicant_name”: {
    “type”: “text”,
    “page”: 1,
    “x”: 100, “y”: 200,
    “width”: 200, “height”: 20,
    ‘value’: “John Doe”  // Add this line
  },
  ...
}
```

### Step 3: Validation

Validate field mappings using `validate_fields.py`:
```bash
python scripts/validate_fields.py fields.json
```

**Output**:
- Verify all required fields are filled
- Check for overlapping fields
- Confirm values are formatted correctly

### Step 4: Form Generation

Generate PDF with `fill_form.py`:
```bash
python scripts/fill_form.py input.pdf fields.json output.pdf
```

## Utility Script Details

### analyze_form.py

**Function**: Extract all input fields from PDF

**Usage**:
```bash
python scripts/analyze_form.py <input.pdf> [--output <fields.json>]
```

**Options**:
- `--output`: Output file (default: stdout)
- `--pages`: Page range to analyze (e.g., 1-3)

### validate_fields.py

**Function**: Validate field mappings and detect issues

**Usage**:
```bash
python scripts/validate_fields.py <fields.json>
```

**Validation items**:
1. Check for required fields
2. Verify type consistency
3. Confirm coordinate boundaries
4. Detect duplicate fields

### fill_form.py

**Function**: Fills PDF forms based on mappings

**Usage**:
```bash
python scripts/fill_form.py <input.pdf> <fields.json> <output.pdf>
```

**Options**:
- `--font`: Font name (default: Helvetica)
- `--font-size`: Font size (default: 10)
```

**scripts/analyze_form.py**:
```python
#!/usr/bin/env python3
“”“PDF form field analysis script”“”

import sys
import json
from pypdf import PdfReader

def analyze_form(pdf_path):
    ‘’“Extract all fields from PDF”" "
    reader = PdfReader(pdf_path)
    fields = {}

    for page_num, page in enumerate(reader.pages, 1):
        if ‘/Annots’ in page:
            for annot in page[‘/Annots’]:
                obj = annot.get_object()
                if obj.get(‘/FT’):  # Field type
                    field_name = obj.get(‘/T’)
                    field_type = obj.get(‘/FT’)
                    rect = obj.get(‘/Rect’)

                    fields[field_name] = {
                        ‘type’: field_type.replace(‘/’, ‘’),
                        ‘page’: page_num,
                        ‘x’: float(rect[0]),                        ‘y’: float(rect[1]),
                        ‘width’: float(rect[2]) - float(rect[0]),
                        ‘height’: float(rect[3]) - float(rect[1])
                    }

    return fields

if __name__ == ‘__main__’:
    if len(sys.argv) < 2:
        print(“Usage: python analyze_form.py <input.pdf>”)
        sys.exit(1)

    pdf_path = sys.argv[1]
    fields = analyze_form(pdf_path)
    print(json.dumps(fields, indent=2))
```

---

## Domain-Specific Examples

### Backend Development

```markdown
---
name: fastapi-crud
description: Build CRUD API endpoints with FastAPI, including validation, error handling, and database integration. Use when creating REST APIs with FastAPI.
---

# FastAPI CRUD Pattern

## Basic Structure

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

app = FastAPI()

# Models
class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float

class ItemResponse(ItemCreate):
    id: int

    class Config:
        from_attributes = True

# Endpoint
@app.post(“/items/”, response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get(“/items/{item_id}”, response_model=ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")    return item
```

## For detailed patterns, refer to [PATTERNS.md](PATTERNS.md)
```

### Frontend Development

```markdown
---
name: react-component-patterns
description: Build React components following best practices with TypeScript, hooks, and proper error handling. Use when creating React components.
---

# React Component Patterns

## Basic Component

```typescript
import React, { useState, useEffect } from ‘react’;

interface UserProps {
  userId: string;
}

export const UserProfile: React.FC<UserProps> = ({ userId }) => {
  const [user, setUser] = useState<User | null>(null);  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(res => res.json())
      .then(data => {
        setUser(data);
        setLoading(false);      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return <div>User not found</div>;  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
};
```

## Advanced patterns are in [ADVANCED.md] (ADVANCED.md)
```

---

## Quick Start Guide

### 1. Create a Simple Skill (5 min)

```bash
mkdir my-skill
cd my-skill
```

Create `SKILL.md`:
```markdown
---
name: my-first-skill
description: [What it does]. Use when [When to use it].
---

# My First Skill

## Quick start

[Core example]

```python
# Code
```
```

### 2. Add Progressive Disclosure (10 minutes)

```bash
touch ADVANCED.md
touch REFERENCE.md
```

Modify `SKILL.md`:
```markdown
## Advanced Features

For more details, see the following references:
- **Advanced Usage**: [ADVANCED.md](ADVANCED.md)
- **API Reference**: [REFERENCE.md](REFERENCE.md)
```

### 3. Add Scripts (15 minutes)

```bash
mkdir scripts
```

Write utility scripts and reference them in `SKILL.md`

---

## Next Steps

1. Read **Best Practices Documentation**: [CLAUDE_SKILLS_BEST_PRACTICES.md](CLAUDE_SKILLS_BEST_PRACTICES.md)
2. Consult the **Official Cookbook**: https://github.com/anthropics/claude-cookbooks/tree/main/skills
3. **Test with Claude**: Use it practically and refine
4. **Gather Feedback**: Observe how Claude navigates

---

## Change History

- **2025-10-28**: Initial version created