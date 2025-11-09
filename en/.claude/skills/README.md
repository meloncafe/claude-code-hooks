- [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills) - Official Examples

### API Documentation
- [Use Skills with the Claude API](https://docs.anthropic.com/en/api/skills-guide)
- [Use Skills in Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)

### Blog
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

---

## 💡 Key Principles Summary

### 1. Concise is Key
Claude already knows the basics. Provide only essential execution steps.

### 2. Progressive Disclosure
- **Level 1**: Metadata (Always load) - ~100 tokens
- **Level 2**: Instructions (When triggered) - ~5k tokens
- **Level 3**: Resources (When needed) - Unlimited

### 3. Appropriate Freedom
- Creative tasks → High freedom
- Repetitive tasks → Provide templates
- Precision tasks → Precise instructions

### 4. Executable Code
- Start with minimal examples
- Include error handling
- Utilize scripts

### 5. Clear Triggers
```yaml
description: [What]. Use when [When].
```

---

## 📊 Structure Comparison

### Simple Skill (Sufficient for most cases)
```
my-skill/
└── SKILL.md          # ~2-5KB, all content
```

### Progressive Disclosure (For complex cases)
```
my-skill/
├── SKILL.md          # ~2KB, general cases
├── ADVANCED.md       # ~3KB, advanced features
├── REFERENCE.md      # ~2KB, API reference
└── scripts/
    └── helper.py     # utilities
```

### Domain-Specific Organization (Large Scale)
```
bigquery-skill/
├── SKILL.md          # Navigation
└── reference/
    ├── finance.md    # Finance Schema
    ├── sales.md      # Sales Schema
    └── product.md    # Product Schema
```

---

## ✅ Quick Checklist

### Required Items
- [ ] YAML frontmatter (`name`, `description`)
- [ ] Quick start section
- [ ] Executable example
- [ ] Clear trigger (`Use when...`)

### Quality Items
- [ ] Concise description
- [ ] Unix path (`/`)
- [ ] Time-independent
- [ ] Consistent terminology


### Advanced items
- [ ] Progressive disclosure
- [ ] Workflow checklist
- [ ] Utility script
- [ ] Feedback loop

---

## 🎓 Further Learning

### Community
- [Discord](https://www.anthropic.com/discord)
- [Support Center](https://support.claude.com/)

### Documentation
- [Claude Docs](https://docs.anthropic.com/)
- [API Reference](https://docs.anthropic.com/en/api/messages)

---

## 📝 Document Information

- **Date Created**: 2025-10-28
- **Version**: 1.0
- **Based On**: Anthropic Official Documentation (as of 2025-10-28)
- **Language**: Korean

---

## 🚀 Next Steps

1. **Quick Start**: QUICK_REFERENCE.md → "Quick Start Template"
2. **Understand**: Read CLAUDE_SKILLS_BEST_PRACTICES.md thoroughly
3. **Practice**: Follow the examples in TEMPLATES_AND_EXAMPLES.md
4. **Optimize**: Validate using the checklist in QUICK_REFERENCE.md

Happy Skill Building! 🎉
# Claude Agent Skills Best Practices Comprehensive Guide 📚

> **Based on Anthropic Official Documentation** - Includes practical examples and templates

## 📖 Document Structure

### 1. [CLAUDE_SKILLS_BEST_PRACTICES.md](CLAUDE_SKILLS_BEST_PRACTICES.md) (Main Guide)
**Complete Best Practices Guide** - Summarizes all content from Anthropic's official documentation in Korean

**Includes**:
- ✅ What are Skills?
- ✅ Core Principles (Conciseness, Freedom Settings, Model Testing)
- ✅ Skills Structure and YAML Frontmatter
- ✅ Writing Best Practices
- ✅ Progressive Disclosure Pattern
- ✅ Workflow Design (Checklist, Feedback Loop)
- ✅ How to Include Executable Code
- ✅ Anti-Patterns (Things to Avoid)
- ✅ Complete Checklist
- ✅ General Pattern Library

**Reading Time**: 30-40 minutes
**Purpose**: When you want to properly understand Skills from the ground up

---

### 2. [TEMPLATES_AND_EXAMPLES.md](TEMPLATES_AND_EXAMPLES.md) (Practical Examples)
**A collection of ready-to-use templates and examples**

**Includes**:
- ✅ Basic Skill template
- ✅ Practical example of Progressive Disclosure
  - Document Processing (DOCX)
  - Data Analysis (BigQuery)
- ✅ Workflow Examples
  - Checklist-Based (Code Review)
  - Feedback Loop (API Integration)
- ✅ Code-Included Examples
  - Utility Scripts
  - PDF Form Processing
- ✅ Domain-Specific Examples
  - Backend (FastAPI CRUD)
  - Frontend (React Components)

**Reading Time**: 20-30 minutes
**Purpose**: When you want to get started quickly or need reference examples

---

### 3. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (Quick Reference)
**Checklists and Cheat Sheets - Guides to keep by your desk**

**Includes**:
- ✅ Skill Creation Checklist
- ✅ Quick Start Templates
- ✅ SKILL.md Templates (Basic, Progressive, Workflow)
- ✅ Best Practices Cheat Sheet (DO / DON'T)
- ✅ Description Writing Formula
- ✅ Frequently Used Patterns
- ✅ Token Optimization Guide
- ✅ Development Workflow (Phase-by-Phase)
- ✅ Troubleshooting Guide
- ✅ Success Metrics

**Reading Time**: 10-15 minutes
**Purpose**: When you need quick reference or a checklist

---

## 🎯 Which document should I read first?

### Scenario 1: "I don't know what Skills are"
1. Read **CLAUDE_SKILLS_BEST_PRACTICES.md** from start to finish
2. Browse examples in **TEMPLATES_AND_EXAMPLES.md**
3. Bookmark **QUICK_REFERENCE.md**

### Scenario 2: "I want to build one quickly"
1. **QUICK_REFERENCE.md** "Quick Start Templates" section
2. **TEMPLATES_AND_EXAMPLES.md** "Basic Skill Template"
3. Build while checking the **QUICK_REFERENCE.md** checklist

### Scenario 3: "I need advanced features"
1. **CLAUDE_SKILLS_BEST_PRACTICES.md** "Progressive Disclosure pattern"
2. **TEMPLATES_AND_EXAMPLES.md** "Progressive Disclosure practical example"
3. **QUICK_REFERENCE.md** "Token optimization guide"

### Scenario 4: "Something isn't working and I don't know why"
1. **QUICK_REFERENCE.md** "Troubleshooting" section
2. **CLAUDE_SKILLS_BEST_PRACTICES.md** "Anti-patterns" section
3. **QUICK_REFERENCE.md** Verify using the "Checklist"

---

## 📚 Learning Path

### Beginner (1-2 hours)
1. ✅ Read QUICK_REFERENCE.md
2. ✅ Create one simple Skill
3. ✅ Test with Claude

### Intermediate (3-5 hours)
1. ✅ Thoroughly read CLAUDE_SKILLS_BEST_PRACTICES.md
2. ✅ Try applying Progressive Disclosure
3. ✅ Apply to a real project


### Advanced (1 day)
1. ✅ Understand all examples in TEMPLATES_AND_EXAMPLES.md
2. ✅ Create a complex workflow Skill
3. ✅ Apply token optimization

---

## 🔗 Official Resources

### Essential Documentation
- [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) - Official overview
- [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices) - Official best practices
- [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart) - Quick start
