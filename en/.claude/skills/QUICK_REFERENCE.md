# My Skill

## Quick start

```python
# TODO: Minimal example
```
EOF

# 3. Test with Claude
```

### Phase 2: Improvement (1-2 hours)

```bash
# 1. Observe usage patterns
# 2. Identify frequently referenced content
# 3. Add progressive disclosure

touch ADVANCED.md
touch REFERENCE.md

# 4. Update SKILL.md (Add reference links)
```

### Phase 3: Optimization (1 hour)

```bash
# 1. Move repetitive logic to scripts
mkdir scripts
# Write scripts...

# 2. Document script usage in SKILL.md
# 3. Final testing
```

---

## 🎓 Learning Resources

### Required Reading
1. [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
2. [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
3. [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)

### Practical Examples
- [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills)
- [Pre-built Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview#pre-built-agent-skills): pptx, xlsx, docx, pdf

### Advanced Learning
- [Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [API Guide](https://docs.anthropic.com/en/api/skills-guide)
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)

---

## 🐛 Troubleshooting

### Claude Not Using the Skill

**Cause 1**: Unclear Description
- **Solution**: Add a clear trigger keyword


**Cause 2**: Name is too generic
- **Solution**: Use a specific name (e.g., `helper` → `pdf-form-filling`)


**Cause 3**: Conflict with another Skill
- **Solution**: Differentiate the Description


### Claude uses the wrong Skill

**Cause**: Overlapping descriptions
- **Solution**: Clearly define each skill's boundaries

### Excessive token usage

**Cause**: SKILL.md is too large
- **Solution**: Apply progressive disclosure

---

## 📊 Success Metrics

### Signals That the Skill Works Well

- ✅ Claude selects automatically
- ✅ Only necessary files are loaded
- ✅ Correct result on first attempt
- ✅ Self-recovery upon error

### Signals That Need Improvement

- ❌ Claude does not select
- ❌ Unnecessary files are loaded
- ❌ Success only after multiple attempts
- ❌ User intervention required when errors occur

---

## 🔄 Version Management

### When Updating the Skill

1. **Document Changes**
   ```markdown
   ## Change History

   - **2025-10-28**: v1.1 - [Changes]
   - **2025-10-20**: v1.0 - Initial release
```

2. **Maintain backward compatibility**
   - Ensure existing workflows remain intact
   - Specify version for major changes

3. **Retest All Examples**
   - Re-validate all examples
   - Verify edge cases

---

## 📞 Get Help

### Community
- [Discord](https://www.anthropic.com/discord)
- [Support Center](https://support.claude.com/)

### Documentation
- [Claude Docs](https://docs.anthropic.com/)
- [API Reference](https://docs.anthropic.com/en/api/messages)

---

**Last Updated**: October 28, 2025
**Document Version**: 1.0
| More than 3 nested steps | Claude gets confused |
| Assuming tool names | Use server:tool format |
| Unclear triggers | Claude doesn't know when to use it |
| Assuming installation | Explicit installation command |

---

## 🎯 Description Writing Formula

### Formula: `[Function]. Use when [Trigger].`

### Good Example

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

### Bad Example

```yaml
description: Helps with documents
```


### Selecting Trigger Keywords
| Domain | Good Keywords | Bad Keywords |
|--------|-------------|-------------|
| PDF | "PDF files", "document extraction", "forms" | "files", "documents" |
| API | "REST API", "endpoints", "HTTP requests" | "network", "web" |
| Database | "SQL queries", "database schema", "transactions" | "data", "storage" |

---

## 🔧 Common Patterns

### Pattern 1: Providing Templates

```markdown
## [Task Name]

Use the following template and adjust as needed:

```python
def template_function(param):
    # Base structure
    pass
```

**Customization**:
- [Option 1]: [Description]
- [Option 2]: [Description]
```


### Pattern 2: Conditional Branching


```markdown
## [Task Name]


**Scenario 1**: [Condition] → [Solution A]
**Scenario 2**: [Condition] → [Solution B]
**Scenario 3**: [Condition] → [Solution C]
```


### Pattern 3: Checklist


```markdown
## [Task Name]


```
Progress:
- [ ] Step 1: [Action]
- [ ] Step 2: [Action]
- [ ] Step 3: [Action]
```

Check off each step as completed.
```


### Pattern 4: Feedback Loop


```markdown
## [Task Name]

1. [Action]
2. **Verification**: [Checklist]
3. If verification fails:
   - [Diagnose issue]
   - [Fix]
   - Return to Step 2
4. **Continue only if verification passes**
5. [Next Step]
```

---

## 📐 Token Optimization Guide

### Token Cost by Level

| Level | Description | Token Cost | Loading Point |
|------|------|-----------|-----------|
| 1 | YAML frontmatter | ~100 tokens | Always |
| 2 | SKILL.md body | ~2-5k tokens | Triggered |
| 3+ | Additional files | Variable | Referenced |
| Script | Script execution | Output only (~100 tokens) | Execution |

### Optimization Strategy

1. **Keep metadata concise**: Description should be core only
2. **Compress SKILL.md**: Cover only 80% of cases
3. **Progressive disclosure**: Place the rest in separate files
4. **Utilize scripts**: Move repetitive logic to scripts

### Example: Token Reduction

#### ❌ Before (8000 tokens)

```
my-skill/
└── SKILL.md (8000 tokens - includes all content)
```

#### ✅ After (2500 tokens for 80% of cases)

```
my-skill/
├── SKILL.md (2000 tokens - general cases)
├── ADVANCED.md (3000 tokens - advanced, loaded only when needed)
├── REFERENCE.md (2000 tokens - API, loaded only when needed)
└── scripts/
    └── validate.py (Execution only, 0 tokens)
```

**Savings**: 75% (for most cases)

---

## 🛠️ Development Workflow

### Phase 1: Prototype (30 minutes)

```bash
# 1. Create directory
mkdir my-skill && cd my-skill

# 2. Create minimal SKILL.md
cat > SKILL.md << 'EOF'
---
name: my-skill
description: [TODO]. Use when [TODO].
---

# Claude Skills Quick Reference Guide

## 📋 Skill Creation Checklist

### Before You Begin
- [ ] Read official documentation: https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview
- [ ] Review existing Skills: https://github.com/anthropics/claude-cookbooks/tree/main/skills
- [ ] Define target use cases

### Essential Components
- [ ] Create `SKILL.md` file
- [ ] Write YAML frontmatter (`name`, `description`)
- [ ] Include a Quick Start section
- [ ] Include executable code examples

### Quality Validation
- [ ] Concise description (remove unnecessary background information)
- [ ] Clear trigger conditions (`Use when...`)
- [ ] Use Unix-style paths (slash `/`)
- [ ] Time-independent content
- [ ] Consistent terminology

### Advanced Features (Optional)
- [ ] Progressive disclosure (additional .md files)
- [ ] Utility scripts (scripts/ folder)
- [ ] Workflow checklist
- [ ] Implement feedback loop

### Testing
- [ ] Tested on target Claude model
- [ ] Validated common use cases
- [ ] Verify edge cases
- [ ] Observe Claude's exploration patterns

---

## 🚀 Quick Start Template

### Create a Skill with a single command

```bash
cat > SKILL.md << 'EOF'
---
name: my-skill
description: [What]. Use when [When].
---

# My Skill

## Quick start

```python
# Code
```
EOF
```

### Minimal Skill Structure

```
my-skill/
└── SKILL.md        # This alone makes it work!
```

### Progressive Disclosure Structure

```
my-skill/
├── SKILL.md        # Main guide (~2-5KB)
├── ADVANCED.md     # Advanced features (load if needed)
├── REFERENCE.md    # API reference (load if needed)
└── scripts/
    └── helper.py   # Execution only, not loaded
```

---

## 📝 SKILL.md Template

### Base Template

```markdown
---
name: skill-name
description: Brief description of what this skill does. Use when user mentions [triggers].
---

# Skill Name

## Quick start

Most common use case with minimal example:

```python
# Core code
```

## Common variations

**Case 1**: Description → Solution
**Case 2**: Description → Solution

## Troubleshooting

**Error X**: Cause → Fix
**Error Y**: Cause → Fix
```

### Progressive Disclosure Template

```markdown
---
name: advanced-skill
description: What it does. Use when [triggers].
---

# Advanced Skill

## Quick start

[Minimal example for 80% of use cases]

## When you need more

**Advanced features**: See [ADVANCED.md](ADVANCED.md)
**Complete API reference**: See [REFERENCE.md](REFERENCE.md)
**Real-world examples**: See [EXAMPLES.md](EXAMPLES.md)

## Troubleshooting

[Common issues and quick fixes]
```

### Workflow Template

```markdown
---
name: workflow-skill
description: Multi-step process. Use when [triggers].
---

# Workflow Skill

## Process

Copy this checklist and track progress:

```
Progress:
- [ ] Step 1: [Action]
- [ ] Step 2: [Action]
- [ ] Step 3: [Action]
```


**Step 1: [Action]**

[Detailed instructions]

**Validation**: [Check point]
- Pass → Step 2
- Fail → [Recovery action]

[Repeat for each step]
```

---

## 💡 Best Practices Cheat Sheet

### ✅ DO (Do)

| Situation | Action |
|------|------|
| Write descriptions | Clearly state what + when |
| Provide examples | Include minimal working code |
| Error handling | Provide alternatives, don't pass the buck |
| Long files | Add a table of contents |
| Complex tasks | Provide a checklist |
| Scripts | Document clear usage instructions |
| Magic numbers | Explain the reason in a comment |
| References | Only nest 1-2 levels |


### ❌ DON'T (Do not do)

| Things to avoid | Reason |
|-------------------|------|
| Windows paths (`\`) | Runs in Unix environments |
| Time references ("before 2025") | Quickly becomes outdated |
| Too many options | Choice overload |
| Verbose explanations | Claude knows basic concepts |
