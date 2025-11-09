# Claude Skills 빠른 참조 가이드

## 📋 Skill 작성 체크리스트

### 시작하기 전
- [ ] 공식 문서 읽기: https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview
- [ ] 기존 Skills 검토: https://github.com/anthropics/claude-cookbooks/tree/main/skills
- [ ] 타겟 사용 사례 정의

### 필수 구성요소
- [ ] `SKILL.md` 파일 생성
- [ ] YAML frontmatter 작성 (`name`, `description`)
- [ ] Quick start 섹션 포함
- [ ] 실행 가능한 코드 예제 포함

### 품질 검증
- [ ] 간결한 설명 (불필요한 배경 정보 제거)
- [ ] 명확한 트리거 조건 (`Use when...`)
- [ ] Unix 스타일 경로 사용 (슬래시 `/`)
- [ ] 시간 독립적 내용
- [ ] 일관된 용어 사용

### 고급 기능 (선택)
- [ ] Progressive disclosure (추가 .md 파일)
- [ ] 유틸리티 스크립트 (scripts/ 폴더)
- [ ] 워크플로우 체크리스트
- [ ] 피드백 루프 구현

### 테스트
- [ ] 타겟 Claude 모델에서 테스트
- [ ] 일반적인 사용 케이스 검증
- [ ] 엣지 케이스 확인
- [ ] Claude 탐색 패턴 관찰

---

## 🚀 빠른 시작 템플릿

### 1줄 명령어로 Skill 생성

```bash
cat > SKILL.md << 'EOF'
---
name: my-skill
description: [무엇을]. Use when [언제].
---

# My Skill

## Quick start

```python
# 코드
```
EOF
```

### 최소 Skill 구조

```
my-skill/
└── SKILL.md        # 이것만 있으면 작동!
```

### Progressive Disclosure 구조

```
my-skill/
├── SKILL.md        # 메인 가이드 (~2-5KB)
├── ADVANCED.md     # 고급 기능 (필요 시 로드)
├── REFERENCE.md    # API 레퍼런스 (필요 시 로드)
└── scripts/
    └── helper.py   # 실행만, 로드 안 됨
```

---

## 📝 SKILL.md 템플릿

### 기본 템플릿

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

### Progressive Disclosure 템플릿

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

### 워크플로우 템플릿

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

## 💡 베스트 프랙티스 치트시트

### ✅ DO (하세요)

| 상황 | 행동 |
|------|------|
| 설명 작성 | 무엇을 + 언제를 명확히 |
| 예제 제공 | 실행 가능한 최소 코드 |
| 에러 처리 | 대안 제공, 떠넘기지 않기 |
| 긴 파일 | 목차 추가 |
| 복잡한 작업 | 체크리스트 제공 |
| 스크립트 | 명확한 사용법 문서화 |
| 매직 넘버 | 주석으로 이유 설명 |
| 참조 | 1-2단계만 중첩 |

### ❌ DON'T (하지 마세요)

| 하지 말아야 할 것 | 이유 |
|-------------------|------|
| Windows 경로 (`\`) | Unix 환경에서 실행 |
| 시간 참조 ("2025년 이전") | 빠르게 구식됨 |
| 너무 많은 옵션 | 선택 과부하 |
| 장황한 설명 | Claude는 기본 개념 앎 |
| 3단계 이상 중첩 | Claude가 헤맴 |
| 툴 이름 가정 | 서버:툴 형식 사용 |
| 불명확한 트리거 | Claude가 언제 사용할지 모름 |
| 설치 가정 | 명시적으로 설치 명령 |

---

## 🎯 Description 작성 공식

### 공식: `[기능]. Use when [트리거].`

### 좋은 예

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

### 나쁜 예

```yaml
description: Helps with documents
```

### 트리거 키워드 선정

| 도메인 | 좋은 키워드 | 나쁜 키워드 |
|--------|-------------|-------------|
| PDF | "PDF files", "document extraction", "forms" | "files", "documents" |
| API | "REST API", "endpoints", "HTTP requests" | "network", "web" |
| Database | "SQL queries", "database schema", "transactions" | "data", "storage" |

---

## 🔧 자주 사용하는 패턴

### 패턴 1: 템플릿 제공

```markdown
## [작업명]

다음 템플릿을 사용하고 필요에 따라 조정하세요:

```python
def template_function(param):
    # 기본 구조
    pass
```

**커스터마이징**:
- [옵션 1]: [설명]
- [옵션 2]: [설명]
```

### 패턴 2: 조건부 분기

```markdown
## [작업명]

**상황 1**: [조건] → [해결책 A]
**상황 2**: [조건] → [해결책 B]
**상황 3**: [조건] → [해결책 C]
```

### 패턴 3: 체크리스트

```markdown
## [작업명]

```
진행 상황:
- [ ] 1단계: [행동]
- [ ] 2단계: [행동]
- [ ] 3단계: [행동]
```

각 단계를 완료하면 체크하세요.
```

### 패턴 4: 피드백 루프

```markdown
## [작업명]

1. [행동]
2. **검증**: [확인 사항]
3. 검증 실패 시:
   - [문제 진단]
   - [수정]
   - 2단계로 돌아가기
4. **검증 통과 시에만 계속**
5. [다음 단계]
```

---

## 📐 토큰 최적화 가이드

### 레벨별 토큰 비용

| 레벨 | 내용 | 토큰 비용 | 로딩 시점 |
|------|------|-----------|-----------|
| 1 | YAML frontmatter | ~100 tokens | 항상 |
| 2 | SKILL.md 본문 | ~2-5k tokens | 트리거 시 |
| 3+ | 추가 파일 | 변동 | 참조 시 |
| Script | 스크립트 실행 | 출력만 (~100 tokens) | 실행 시 |

### 최적화 전략

1. **메타데이터 간결히**: description은 핵심만
2. **SKILL.md 압축**: 80% 케이스만 다룸
3. **Progressive disclosure**: 나머지는 별도 파일
4. **스크립트 활용**: 반복 로직은 스크립트로

### 예시: 토큰 절감

#### ❌ Before (8000 tokens)

```
my-skill/
└── SKILL.md (8000 tokens - 모든 내용 포함)
```

#### ✅ After (2500 tokens for 80% of cases)

```
my-skill/
├── SKILL.md (2000 tokens - 일반 케이스)
├── ADVANCED.md (3000 tokens - 고급, 필요 시만 로드)
├── REFERENCE.md (2000 tokens - API, 필요 시만 로드)
└── scripts/
    └── validate.py (실행만, 토큰 0)
```

**절감**: 75% (대부분의 경우)

---

## 🛠️ 개발 워크플로우

### Phase 1: 프로토타입 (30분)

```bash
# 1. 디렉토리 생성
mkdir my-skill && cd my-skill

# 2. 최소 SKILL.md 작성
cat > SKILL.md << 'EOF'
---
name: my-skill
description: [TODO]. Use when [TODO].
---

# My Skill

## Quick start

```python
# TODO: 최소 예제
```
EOF

# 3. Claude로 테스트
```

### Phase 2: 개선 (1-2시간)

```bash
# 1. 사용 패턴 관찰
# 2. 자주 참조하는 내용 파악
# 3. Progressive disclosure 추가

touch ADVANCED.md
touch REFERENCE.md

# 4. SKILL.md 업데이트 (참조 링크 추가)
```

### Phase 3: 최적화 (1시간)

```bash
# 1. 반복 로직을 스크립트로
mkdir scripts
# 스크립트 작성...

# 2. SKILL.md에서 스크립트 사용법 문서화
# 3. 최종 테스트
```

---

## 🎓 학습 리소스

### 필수 읽기
1. [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
2. [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
3. [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)

### 실전 예제
- [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills)
- [Pre-built Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview#pre-built-agent-skills): pptx, xlsx, docx, pdf

### 심화 학습
- [Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [API Guide](https://docs.anthropic.com/en/api/skills-guide)
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)

---

## 🐛 문제 해결

### Claude가 Skill을 사용하지 않음

**원인 1**: Description이 불명확
- **해결**: 명확한 트리거 키워드 추가

**원인 2**: 이름이 너무 일반적
- **해결**: 구체적인 이름 사용 (예: `helper` → `pdf-form-filling`)

**원인 3**: 다른 Skill과 충돌
- **해결**: Description 차별화

### Claude가 잘못된 Skill 사용

**원인**: Description이 겹침
- **해결**: 각 Skill의 경계를 명확히

### 토큰 사용량이 너무 높음

**원인**: SKILL.md가 너무 큼
- **해결**: Progressive disclosure 적용

---

## 📊 성공 지표

### Skill이 잘 작동하는 신호

- ✅ Claude가 자동으로 선택
- ✅ 필요한 파일만 로드
- ✅ 첫 시도에 올바른 결과
- ✅ 에러 시 자체 복구

### 개선이 필요한 신호

- ❌ Claude가 선택하지 않음
- ❌ 불필요한 파일까지 로드
- ❌ 여러 번 시도 후 성공
- ❌ 에러 시 사용자 개입 필요

---

## 🔄 버전 관리

### Skill 업데이트 시

1. **변경사항 문서화**
   ```markdown
   ## 변경 이력

   - **2025-10-28**: v1.1 - [변경 내용]
   - **2025-10-20**: v1.0 - 초기 버전
   ```

2. **하위 호환성 유지**
   - 기존 워크플로우가 깨지지 않도록
   - 주요 변경 시 버전 명시

3. **테스트 재실행**
   - 모든 예제 재검증
   - 엣지 케이스 확인

---

## 📞 도움 받기

### 커뮤니티
- [Discord](https://www.anthropic.com/discord)
- [Support Center](https://support.claude.com/)

### 문서
- [Claude Docs](https://docs.anthropic.com/)
- [API Reference](https://docs.anthropic.com/en/api/messages)

---

**마지막 업데이트**: 2025-10-28
**문서 버전**: 1.0
