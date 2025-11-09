# Claude Agent Skills Best Practices Guide

> **Official Documentation Source**:
> - [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
> - [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
> - [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)
> - [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills)

## Table of Contents

1. [What Are Skills](#what-are-skills)
2. [Core Principles](#core-principles)
3. [Skills Structure](#skills-structure)
4. [Writing Best Practices](#writing-best-practices)
5. [Progressive Disclosure Pattern](#progressive-disclosure-pattern)
6. [Workflow Design](#workflow-design)
7. [Include Executable Code](#include-executable-code)
8. [Anti-Patterns](#anti-patterns)
9. [Checklist](#checklist)

---

## What Are Skills

### Definition
Agent Skills are modular capabilities that extend Claude's functionality. Each Skill packages **instructions**, **metadata**, and **resources (scripts, templates)** for Claude to automatically use when relevant.
### Why Use Skills?

**Prompts vs. Skills Comparison**:
- **Prompts**: Conversation-level instructions for one-off tasks
- **Skills**: Reusable filesystem-based resources loaded on-demand

**Key Benefits**:
1. **Claude-Specific**: Tailored for domain-specific tasks
2. **Eliminate Repetition**: Automatically reused once created
3. **Combine Capabilities**: Build complex workflows by combining multiple Skills

### How It Works: Progressive Disclosure

Skills use a 3-stage loading system:
| Level | Loading Timing | Token Cost | Content |
|------|-----------|---------- -|------|
| **Level 1: Metadata** | Always (at startup) | ~100 tokens/Skill | `name`, `description` from YAML frontmatter |
| **Level 2: Instructions** | When Skill triggers | Under ~5k tokens | Instructions in SKILL.md body |
| **Level 3: Resources** | When needed | Virtually unlimited | Bundled files executed via bash (content not loaded) |

**Key Point**: Only relevant content is loaded into the context window, so installing many Skills incurs no token penalty.
---

## Core Principles

### 1. Concise is Key

#### ✅ Good Example (Concise Explanation)
```markdown
## PDF Text Extraction

Use pdfplumber to extract text:

```python
import pdfplumber

with pdfplumber.open(“file.pdf”) as pdf:
    text = pdf.pages[0].extract_text()
```
```

#### ❌ Bad Example (Unnecessarily Verbose)
```markdown
## PDF Text Extraction

PDF (Portable Document Format) files are a common file format containing text, images, and other content.
To extract text from a PDF, you need to use a library. While many libraries exist for PDF processing,
we recommend pdfplumber. It's easy to use and handles most cases well.
First, you need to install it using pip...
```

**Principle**: Claude already knows the basic concepts. Provide only the essential steps to execute.
### 2. Set Appropriate Degrees of Freedom

Adjust the degrees of freedom based on the task characteristics:

#### ✅ High Degrees of Freedom (Creative Tasks)
```markdown
## Code Review Process

1. Analyze code structure and organization
2. Identify potential bugs or edge cases
3. Suggest improvements for readability and maintainability
4. Verify compliance with project rules
```

#### ✅ Medium Degrees of Freedom (Template + Customization)
```markdown
## Report Generation

Use the following template and customize as needed:

```python
def generate_report(data, format="markdown", include_charts=True):
    # Process data
    # Generate output in specified format
    # Optionally include visualizations
```
```

#### ✅ Low Freedom (Requires Exact Execution)
```markdown
## Database Migration

Execute this script exactly:

```bash
python scripts/migrate.py --verify --backup
```

Do not modify the command or add additional flags.
```

**Principles**:
- **Creative Tasks** → High Flexibility
- **Repetitive Tasks** → Provide Templates
- **Precision Tasks** → Precise instructions

### 3. Test on All Target Models

Test on all Claude models that will use the Skill. Models may interpret instructions differently.

---

## Skill Structure

### Required File: SKILL.md

Every Skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: pdf-processing
description: Extract text and tables from PDF files, create forms, merge documents. Use when working with PDF files or when users mention PDF, form, or document extraction.
---

# PDF Processing

## Quick start

Text extraction using pdfplumber:

```python
import pdfplumber

with pdfplumber.open(“file.pdf”) as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced Features

**Form Filling**: Full guide in [FORMS.md](FORMS.md)
**API Reference**: All methods in [REFERENCE.md](REFERENCE.md)
```

### YAML Frontmatter Requirements

**Required Fields**:
- `name`: Skill name (max 64 characters)
- `description`: Brief description (max 1024 characters)

**Only these two fields are supported**.

### Naming Conventions

#### ✅ Good names (verb-noun or noun-noun)
```
processing-pdfs
analyzing-spreadsheets
managing-databases
testing-code
writing-documentation
pdf-processing
spreadsheet-analysis
```

#### ❌ Bad names (verb-only, too generic)
```
process-pdfs        # Verb-only (verb-noun OK, verb-only is X)
analyze-spreadsheets  # Verb-only
helper              # Too generic
utils               # Too generic
tools               # Too generic
documents           # Too ambiguous
data                # Too ambiguous
anthropic-helper    # Unnecessary prefix
claude-tools        # Unnecessary prefix
```

### Writing Effective Descriptions

**Structure**: `[Function Description]. Use when [Trigger Condition].`

#### ✅ Good Example
```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

```yaml
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.
```yaml
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

#### ❌ Bad Example (Ambiguous and Insufficient)
```yaml
description: Helps with documents
description: Processes data
description: Does stuff with files
```

**Principles**:
1. Clearly state **what** it does
2. Specify **when** to use it
3. Include **keywords** (PDF, Excel, commit, etc.)

---

## Writing Best Practices

### 1. Avoid Time-Sensitive Information

#### ❌ Bad Example
```markdown
Use the old API before August 2025.
Use the new API after August 2025.
```

#### ✅ Good Example
```markdown
## Current Method

Use v2 API endpoint: `api.example.com/v2/messages`

## Old Pattern

<details>
<summary>Legacy v1 API (deprecated as of 2025-08)</summary>

Use v1 API endpoint: `api.example.com/v1/messages`

This endpoint is no longer supported.
</details>
```

### 2. Use Consistent Terminology

Use the same terms throughout your project:
- “API key” vs “authentication token”
- “user” vs “customer” vs “client”
- “analyze” vs ‘process’ vs “parse”

Choose one and use it consistently.

### 3. Avoid Windows-style paths

#### ✅ Correct path (Unix style)
```markdown
scripts/helper.py
reference/guide.md
```

#### ❌ Incorrect path (Windows style)
```markdown
scripts\helper.py
reference\guide.md
```

**Reason**: Skills runs on Unix-based VMs.
### 4. Avoid Overloading with Too Many Options

#### ❌ Bad Example (Choice Overload)
```markdown
Use one of pypdf, pdfplumber, PyMuPDF, pdf2image, camelot, or tabula-py...
```

#### ✅ Good Example (Default + Alternatives)
```markdown
Use pdfplumber for text extraction:

```python
import pdfplumber
```

For scanned PDFs requiring OCR, use pdf2image + pytesseract instead.
```

**Principle**: Provide one default solution + alternatives for special cases

---

## Progressive Disclosure Pattern

### Pattern 1: High-level guide + reference

```markdown
---
name: pdf-processing
description: Extract text/tables from PDF, create forms, merge documents. Use for PDF operations.
---

# PDF Processing

## Quick start

Text extraction with pdfplumber:

```python
import pdfplumber
with pdfplumber.open(“file.pdf”) as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced Features

**Form Filling**: Full guide in [FORMS.md](FORMS.md)
**API Reference**: All methods in [REFERENCE.md](REFERENCE.md)
** Examples**: Common patterns are documented in [EXAMPLES.md](EXAMPLES.md)
```

### Pattern 2: Domain-Specific Organization

```
bigquery-skill/
├── SKILL.md (Overview and navigation)
└── reference/
    ├── finance.md (Sales, billing metrics)    ├── sales.md (Opportunities, Pipeline)
    ├── product.md (API Usage, Features)
    └── marketing.md (Campaigns, Attribution)
```

```markdown
# BigQuery Data Analysis

## Available Datasets

**Finance**: Revenue, ARR, Billing → See [reference/finance.md](reference/finance.md)
**Sales**: Opportunities, Pipeline, Accounts → See [reference/sales.md](reference/sales.md)
**Product**: API Usage, Features, Adoption → See [reference/product.md](reference/product.md)
**Marketing**: Campaigns, Attribution → See [reference/marketing.md](reference/marketing.md)

## Quick Search

Finding specific metrics:

```bash
grep -i “revenue” reference/finance.md
grep -i “pipeline” reference/sales.md
```
```

### Pattern 3: Conditional Details

```markdown
# DOCX Processing

## Document Generation

New documents use docx-js. See [DOCX-JS.md](DOCX-JS.md).

## Document Editing

Simple edits: Modify XML directly.

**Track Changes**: See [REDLINING.md](REDLINING.md)
**OOXML Details**: See [OOXML.md](OOXML.md)
```

### Caution: Avoid Deep Nested References

#### ❌ Bad Example (3 Levels of Nesting)
```
# SKILL.md
Refer to [advanced.md](advanced.md)...

# advanced.md
Refer to [details.md](details.md)...

# details.md
Actual information goes here...
```

#### ✅ Good Example (1-2 levels)
```markdown
# SKILL.md

**Basic Usage**: [Instructions in SKILL.md]
**Advanced Features**: [advanced.md](advanced.md)
**API Reference**: [reference.md](reference.md)
**Examples**: [examples.md](examples.md)
```

### Add a Table of Contents to Long Reference Files

```markdown
# API Reference

## Table of Contents
- Authentication and Setup
- Core Methods (create, read, update, delete)
- Advanced Features (batch operations, webhooks)
- Error Handling Patterns
- Code Examples

## Authentication and Setup
...

## Core Methods
...
```

---

## Workflow Design

### Use Workflows for Complex Tasks

#### Checklist Pattern

```markdown
## PDF Form Creation Workflow

Copy the following checklist and track your progress:

```
Work in Progress:
- [ ] Step 1: Analyze Form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```

**Step 1: Analyze Form**

Execute: `python scripts/analyze_form.py input.pdf`

Extracts form fields and their positions, saving them to `fields.json`.

**Step 2: Create Field Mappings**

Edit `fields.json` to add values for each field.

**Step 3: Validate Mapping**

Run: `python scripts/validate_fields.py fields.json`

Fix validation errors before proceeding.

**Step 4: Fill the Form**

Run: `python scripts/fill_form.py input.pdf fields.json output.pdf`

**Step 5: Verify Output**

Run: `python scripts/verify_output.py output.pdf`

If validation fails, return to Step 2.
```

### Implementing the Feedback Loop

```markdown
## Document Editing Process

1. Edit `word/document.xml`
2. **Immediate Validation**: `python ooxml/scripts/validate.py unpacked_dir/`
3. If validation fails:
   - Carefully review error messages
   - Fix issues in XML
   - Re-run validation
4. **Proceed only if validation passes**
5. Rebuild: `python ooxml/scripts/pack.py unpacked_dir/ output.docx`
6. Test output document
```

**Principle**: Validate after each step, providing a clear point to return to upon failure

---

## Includes executable code

### 1. Solve, Don't Punt

#### ✅ Good Example (Provides an alternative)
```python
def process_file(path):
    “”“Process file, create if it doesn't exist.”“”
    try:
        with open(path) as f:
            return f.read()    except FileNotFoundError:
        # Create file with default content instead of failing
        print(f“File {path} not found, creating default”)
        with open(path, ‘w’) as f:
            f.write(‘’)
        return ‘’
    except PermissionError:
        # Provide an alternative instead of failing
        print(f“Cannot access {path}, using default”)        return ‘’
```

#### ❌ Bad Example (Passing the buck to Claude)
```python
def process_file(path):
    # Just fail and let Claude handle it
    return open(path).read()
```

### 2. Commenting on Magic Numbers

#### ✅ Good Example
```python
# HTTP requests typically complete within 30 seconds
# Long timeout accounts for slow connections
REQUEST_TIMEOUT = 30

# 3 retries balance reliability and speed
# Most intermittent failures resolve on second retry
MAX_RETRIES = 3
```

#### ❌ Bad Example
```python
TIMEOUT = 47  # Why 47?
RETRIES = 5   # Why 5?
```

### 3. Provide Utility Scripts

```markdown
## Utility Scripts

**analyze_form.py**: Extract all form fields from PDF

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

Output format:
```json
{
  “field_name”: {“type”: “text”, ‘x’: 100, “y”: 200},  “signature”: {“type”: “sig”, “x”: 150, ‘y’: 500}
}
```

**validate_boxes.py**: Check overlapping bounding boxes

```bash
python scripts/validate_boxes.py fields.json
# Returns: “OK” or a list of conflicts
```

**fill_form.py**: Apply field values to PDF

```bash
python scripts/fill_form.py input.pdf fields.json output.pdf
```
```

### 4. Using Visual Analysis

```markdown
## Analyzing Form Layout

1. Convert PDF to images:
   ```bash
   python scripts/pdf_to_images.py form.pdf
   ```

2. Analyze each page image to identify form fields
3. Claude can visually see field positions and types
```

### 5. Generating Validatable Intermediate Output

```markdown
## Document Change Workflow

1. Record changes in `changes.json`:
   ```json
   {
     “page”: 1,
     “section”: “introduction”,
     ‘change’: “Added new paragraph about...”
   }
   ```

2. Validate changes:
   ```bash
   python scripts/validate_changes.py changes.json   ```

3. Apply if validated:
   ```bash
   python scripts/apply_changes.py document.xml changes.json
   ```
```

---

## Anti-Patterns

### 1. ❌ Not assuming installation

#### Bad Example
```markdown
Use a PDF library to process the file.
```

#### Good Example
```markdown
Install required packages: `pip install pypdf`

Then use:
```python
from pypdf import PdfReader
reader = PdfReader(“file.pdf”)
```
```

### 2. ❌ Do not assume MCP tool names are server names

#### Bad Example
```markdown
Use the `BigQuery` tool.
Use the `GitHub` tool.
```

#### Good Example
```markdown
Use the `BigQuery:bigquery_schema` tool to retrieve table schemas.
Use the `GitHub:create_issue` tool to create issues.
```

**Format**: `ServerName:tool_name`

### 3. ❌ Do not provide flexibility in templates

#### Bad example (too rigid)
```markdown
## Report Structure

**Always** use this exact template structure:

```markdown
# [Analysis Title]

## Summary
[One-paragraph overview of key findings]

## Key Findings
- Finding 1 (supported by data)
- Finding 2 (supported by data)
```
```

#### Good Example (Reasonable Defaults + Flexibility)
```markdown
## Report Structure

The following is a reasonable default format, but use it based on your analysis:

```markdown
# [Analysis Title]

## Summary
[Overview]

## Key Findings
[Adjust sections based on findings]

## Recommendations
[Tailored to specific context]
```

Adjust sections as needed for specific analysis types.
```

---

## Checklist

### Core Qualities

- [ ] **Conciseness**: Actionable instructions only, without unnecessary explanations
- [ ] **Clear Trigger**: Description clearly states when to use
- [ ] **Consistent Terminology**: Same words for same concepts
- [ ] **Unix Paths**: All file paths use forward slashes (/)
- [ ] **Time-Independent**: No references to dates or times
- [ ] **Model Testing**: Tested on all Claude models to be used

### Skill Structure

- [ ] **YAML Frontmatter**: Includes `name` and `description` fields
- [ ] **Character Limits**: name ≤ 64 characters, description ≤ 1024 characters
- [ ] **Progressive disclosure**: Additional reference files linked only when needed
- [ ] **Table of contents**: Include a table of contents for long files (>500 lines)
- [ ] **1-2 step references**: Avoid nesting more than 3 steps

### Workflow

- [ ] **Checklist**: Provide a copyable checklist for complex tasks
- [ ] **Clear steps**: Each step is explicit and actionable
- [ ] **Feedback loop**: Specify verification steps and fallback points upon failure
- [ ] **Conditional branching**: Clearly define “if X, do Y” patterns

### Code and scripts

- [ ] **Provide alternatives**: Scripts handle common failure cases
- [ ] **Magic number comments**: Explain reasons for hardcoded values
- [ ] **Clear output**: Document script output format
- [ ] **Dependency specification**: Specify required packages and installation methods
- [ ] **Visual analysis**: Provide image conversion tools when needed

### Testing

- [ ] **Evaluation Cases**: At least 3-5 representative test cases
- [ ] **Success Criteria**: Define expected behavior for each case
- [ ] **Failure Cases**: Test common failure scenarios
- [ ] **Edge Cases**: Test boundary conditions
- [ ] **Iterative Improvement**: Observe Claude usage patterns and refine

---

## General Pattern Library

### Template Patterns

```markdown
## Commit Message Format

Generate commit messages following these examples:

**Example 1:**
Input: Added user authentication with JWT token
Output:
```
feat(auth): Implemented JWT-based authentication

Added login endpoint and token validation middleware
```

**Example 2:**
Input: Fixed bug where date displayed incorrectly in reports
Output:
```
fix(reports): Modified date format in time zone conversion

Consistently use UTC timestamps throughout report generation
```

Follow this style: type(scope): Brief description, then detailed explanation.
```

### Conditional Workflow Pattern

```markdown
## Document Modification Workflow

1. Determine modification type:

   **Creating new content?** → Follow “Creation Workflow” below   **Editing existing content?** → Follow the “Editing Workflow” below

2. Creation Workflow:
   - Use the docx-js library
   - Build the document from scratch
   - Export in .docx format

3. Editing Workflow:
   - Unzip the existing document
   - Directly modify the XML
   - Validate after each change
   - Rezip upon completion
```

---

## Reference Materials

### Official Documentation
- [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
- [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)
- [Use Skills with the Claude API](https://docs.anthropic.com/en/api/skills-guide)
- [Use Skills in Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)

### Examples
- [Skills Cookbook (GitHub)](https://github.com/anthropics/claude-cookbooks/tree/main/skills)

### Blog
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

---

## Change History

- **2025-10-28**: Initial version created (based on Anthropic official documentation)