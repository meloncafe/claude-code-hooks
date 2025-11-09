# Claude Agent Skills 베스트 프랙티스 종합 가이드 📚

> **Anthropic 공식 문서 기반** - 실전 예제와 템플릿 포함

## 📖 문서 구성

### 1. [CLAUDE_SKILLS_BEST_PRACTICES.md](CLAUDE_SKILLS_BEST_PRACTICES.md) (메인 가이드)
**완전한 베스트 프랙티스 가이드** - Anthropic 공식 문서의 모든 내용을 한국어로 정리

**포함 내용**:
- ✅ Skills란 무엇인가
- ✅ 핵심 원칙 (간결함, 자유도 설정, 모델 테스트)
- ✅ Skills 구조와 YAML frontmatter
- ✅ 작성 베스트 프랙티스
- ✅ Progressive Disclosure 패턴
- ✅ 워크플로우 설계 (체크리스트, 피드백 루프)
- ✅ 실행 가능한 코드 포함 방법
- ✅ 안티패턴 (피해야 할 것들)
- ✅ 완전한 체크리스트
- ✅ 일반 패턴 라이브러리

**읽는 시간**: 30-40분
**용도**: 처음부터 Skills를 제대로 이해하고 싶을 때

---

### 2. [TEMPLATES_AND_EXAMPLES.md](TEMPLATES_AND_EXAMPLES.md) (실전 예제)
**바로 사용할 수 있는 템플릿과 예제 모음**

**포함 내용**:
- ✅ 기본 Skill 템플릿
- ✅ Progressive Disclosure 실전 예제
  - 문서 처리 (DOCX)
  - 데이터 분석 (BigQuery)
- ✅ 워크플로우 예제
  - 체크리스트 기반 (코드 리뷰)
  - 피드백 루프 (API 통합)
- ✅ 코드 포함 예제
  - 유틸리티 스크립트
  - PDF 양식 처리
- ✅ 도메인별 예제
  - 백엔드 (FastAPI CRUD)
  - 프론트엔드 (React 컴포넌트)

**읽는 시간**: 20-30분
**용도**: 빠르게 시작하고 싶을 때, 참고할 예제가 필요할 때

---

### 3. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (빠른 참조)
**체크리스트와 치트시트 - 책상 옆에 두고 보는 가이드**

**포함 내용**:
- ✅ Skill 작성 체크리스트
- ✅ 빠른 시작 템플릿
- ✅ SKILL.md 템플릿 (기본, Progressive, 워크플로우)
- ✅ 베스트 프랙티스 치트시트 (DO / DON'T)
- ✅ Description 작성 공식
- ✅ 자주 사용하는 패턴
- ✅ 토큰 최적화 가이드
- ✅ 개발 워크플로우 (Phase별)
- ✅ 문제 해결 가이드
- ✅ 성공 지표

**읽는 시간**: 10-15분
**용도**: 빠르게 참고하고 싶을 때, 체크리스트가 필요할 때

---

## 🎯 어떤 문서부터 읽어야 할까?

### 시나리오 1: "Skills가 뭔지 모르겠어요"
1. **CLAUDE_SKILLS_BEST_PRACTICES.md** 처음부터 끝까지 읽기
2. **TEMPLATES_AND_EXAMPLES.md**에서 예제 구경
3. **QUICK_REFERENCE.md** 북마크

### 시나리오 2: "빠르게 하나 만들어보고 싶어요"
1. **QUICK_REFERENCE.md** "빠른 시작 템플릿" 섹션
2. **TEMPLATES_AND_EXAMPLES.md** "기본 Skill 템플릿"
3. 만들면서 **QUICK_REFERENCE.md** 체크리스트 확인

### 시나리오 3: "고급 기능이 필요해요"
1. **CLAUDE_SKILLS_BEST_PRACTICES.md** "Progressive Disclosure 패턴"
2. **TEMPLATES_AND_EXAMPLES.md** "Progressive Disclosure 실전 예제"
3. **QUICK_REFERENCE.md** "토큰 최적화 가이드"

### 시나리오 4: "뭔가 안 되는데 왜 그런지 모르겠어요"
1. **QUICK_REFERENCE.md** "문제 해결" 섹션
2. **CLAUDE_SKILLS_BEST_PRACTICES.md** "안티패턴" 섹션
3. **QUICK_REFERENCE.md** "체크리스트"로 검증

---

## 📚 학습 경로

### 초급 (1-2시간)
1. ✅ QUICK_REFERENCE.md 읽기
2. ✅ 간단한 Skill 하나 만들기
3. ✅ Claude로 테스트

### 중급 (3-5시간)
1. ✅ CLAUDE_SKILLS_BEST_PRACTICES.md 정독
2. ✅ Progressive Disclosure 적용해보기
3. ✅ 실제 프로젝트에 적용

### 고급 (1일)
1. ✅ TEMPLATES_AND_EXAMPLES.md 모든 예제 이해
2. ✅ 복잡한 워크플로우 Skill 만들기
3. ✅ 토큰 최적화 적용

---

## 🔗 공식 리소스

### 필수 문서
- [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) - 공식 개요
- [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices) - 공식 베스트 프랙티스
- [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart) - 빠른 시작
- [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills) - 공식 예제

### API 문서
- [Use Skills with the Claude API](https://docs.anthropic.com/en/api/skills-guide)
- [Use Skills in Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)

### 블로그
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

---

## 💡 핵심 원칙 요약

### 1. 간결함이 핵심 (Concise is Key)
Claude는 이미 기본 개념을 알고 있습니다. 필수 실행 단계만 제공하세요.

### 2. Progressive Disclosure
- **Level 1**: Metadata (항상 로드) - ~100 tokens
- **Level 2**: Instructions (트리거 시) - ~5k tokens
- **Level 3**: Resources (필요 시) - 무제한

### 3. 적절한 자유도
- 창의적 작업 → 높은 자유도
- 반복 작업 → 템플릿 제공
- 정밀 작업 → 정확한 지침

### 4. 실행 가능한 코드
- 최소 예제부터 시작
- 에러 처리 포함
- 스크립트 활용

### 5. 명확한 트리거
```yaml
description: [무엇을]. Use when [언제].
```

---

## 📊 구조 비교

### 단순 Skill (대부분의 경우 충분)
```
my-skill/
└── SKILL.md          # ~2-5KB, 모든 내용
```

### Progressive Disclosure (복잡한 경우)
```
my-skill/
├── SKILL.md          # ~2KB, 일반 케이스
├── ADVANCED.md       # ~3KB, 고급 기능
├── REFERENCE.md      # ~2KB, API 레퍼런스
└── scripts/
    └── helper.py     # 유틸리티
```

### 도메인별 조직 (대규모)
```
bigquery-skill/
├── SKILL.md          # 네비게이션
└── reference/
    ├── finance.md    # 재무 스키마
    ├── sales.md      # 영업 스키마
    └── product.md    # 제품 스키마
```

---

## ✅ 빠른 체크리스트

### 필수 항목
- [ ] YAML frontmatter (`name`, `description`)
- [ ] Quick start 섹션
- [ ] 실행 가능한 예제
- [ ] 명확한 트리거 (`Use when...`)

### 품질 항목
- [ ] 간결한 설명
- [ ] Unix 경로 (`/`)
- [ ] 시간 독립적
- [ ] 일관된 용어

### 고급 항목
- [ ] Progressive disclosure
- [ ] 워크플로우 체크리스트
- [ ] 유틸리티 스크립트
- [ ] 피드백 루프

---

## 🎓 추가 학습

### 커뮤니티
- [Discord](https://www.anthropic.com/discord)
- [Support Center](https://support.claude.com/)

### 문서
- [Claude Docs](https://docs.anthropic.com/)
- [API Reference](https://docs.anthropic.com/en/api/messages)

---

## 📝 문서 정보

- **작성 일자**: 2025-10-28
- **버전**: 1.0
- **기반**: Anthropic 공식 문서 (2025-10-28 기준)
- **언어**: 한국어

---

## 🚀 다음 단계

1. **빠른 시작**: QUICK_REFERENCE.md → "빠른 시작 템플릿"
2. **이해하기**: CLAUDE_SKILLS_BEST_PRACTICES.md 정독
3. **실습하기**: TEMPLATES_AND_EXAMPLES.md 예제 따라하기
4. **최적화**: QUICK_REFERENCE.md 체크리스트로 검증

Happy Skill Building! 🎉
