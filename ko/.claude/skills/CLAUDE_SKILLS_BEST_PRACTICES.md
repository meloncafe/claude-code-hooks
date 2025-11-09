# Claude Agent Skills 베스트 프랙티스 가이드

> **공식 문서 출처**:
> - [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
> - [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
> - [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)
> - [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills)

## 목차

1. [Skills란 무엇인가](#skills란-무엇인가)
2. [핵심 원칙](#핵심-원칙)
3. [Skills 구조](#skills-구조)
4. [작성 베스트 프랙티스](#작성-베스트-프랙티스)
5. [Progressive Disclosure 패턴](#progressive-disclosure-패턴)
6. [워크플로우 설계](#워크플로우-설계)
7. [실행 가능한 코드 포함](#실행-가능한-코드-포함)
8. [안티패턴](#안티패턴)
9. [체크리스트](#체크리스트)

---

## Skills란 무엇인가

### 정의
Agent Skills는 Claude의 기능을 확장하는 모듈형 역량입니다. 각 Skill은 **지침(instructions)**, **메타데이터**, **리소스(scripts, templates)**를 패키징하여 Claude가 관련성이 있을 때 자동으로 사용합니다.

### 왜 Skills를 사용하는가?

**프롬프트 vs Skills 비교**:
- **프롬프트**: 일회성 작업을 위한 대화 수준의 지침
- **Skills**: 온디맨드로 로드되는 재사용 가능한 파일시스템 기반 리소스

**주요 이점**:
1. **Claude 특화**: 도메인별 작업에 맞춤화
2. **반복 제거**: 한 번 생성하면 자동으로 사용
3. **역량 조합**: 여러 Skills를 결합하여 복잡한 워크플로우 구축

### 작동 원리: Progressive Disclosure (점진적 공개)

Skills는 3단계 로딩 시스템을 사용합니다:

| 레벨 | 로딩 시점 | 토큰 비용 | 내용 |
|------|-----------|-----------|------|
| **Level 1: Metadata** | 항상 (시작 시) | ~100 tokens/Skill | YAML frontmatter의 `name`, `description` |
| **Level 2: Instructions** | Skill 트리거 시 | ~5k tokens 미만 | SKILL.md 본문의 지침 |
| **Level 3: Resources** | 필요 시 | 사실상 무제한 | bash로 실행되는 번들 파일 (내용 로드 안 됨) |

**핵심**: 관련 내용만 컨텍스트 윈도우에 로드되므로 많은 Skills를 설치해도 토큰 페널티가 없습니다.

---

## 핵심 원칙

### 1. 간결함이 핵심 (Concise is Key)

#### ✅ 좋은 예 (간결한 설명)
```markdown
## PDF 텍스트 추출

pdfplumber를 사용하여 텍스트 추출:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

#### ❌ 나쁜 예 (불필요하게 장황함)
```markdown
## PDF 텍스트 추출

PDF (Portable Document Format) 파일은 텍스트, 이미지 및 기타 콘텐츠를 포함하는 일반적인 파일 형식입니다.
PDF에서 텍스트를 추출하려면 라이브러리를 사용해야 합니다. PDF 처리를 위한 라이브러리는 많이 있지만
pdfplumber를 권장합니다. 사용하기 쉽고 대부분의 경우를 잘 처리하기 때문입니다.
먼저 pip를 사용하여 설치해야 합니다...
```

**원칙**: Claude는 이미 기본 개념을 알고 있습니다. 필수 실행 단계만 제공하세요.

### 2. 적절한 자유도 설정 (Set Appropriate Degrees of Freedom)

작업 특성에 따라 자유도를 조정하세요:

#### ✅ 높은 자유도 (창의적 작업)
```markdown
## 코드 리뷰 프로세스

1. 코드 구조와 조직 분석
2. 잠재적 버그나 엣지 케이스 확인
3. 가독성 및 유지보수성 개선 제안
4. 프로젝트 규칙 준수 여부 검증
```

#### ✅ 중간 자유도 (템플릿 + 커스터마이징)
```markdown
## 보고서 생성

다음 템플릿을 사용하고 필요에 따라 커스터마이징하세요:

```python
def generate_report(data, format="markdown", include_charts=True):
    # 데이터 처리
    # 지정된 형식으로 출력 생성
    # 선택적으로 시각화 포함
```
```

#### ✅ 낮은 자유도 (정확한 실행 필요)
```markdown
## 데이터베이스 마이그레이션

정확히 이 스크립트를 실행하세요:

```bash
python scripts/migrate.py --verify --backup
```

명령을 수정하거나 추가 플래그를 추가하지 마세요.
```

**원칙**:
- **창의적 작업** → 높은 자유도
- **반복 작업** → 템플릿 제공
- **정밀 작업** → 정확한 지침

### 3. 모든 타겟 모델에서 테스트

Skills를 사용할 모든 Claude 모델에서 테스트하세요. 모델마다 지침 해석 방식이 다를 수 있습니다.

---

## Skills 구조

### 필수 파일: SKILL.md

모든 Skill은 YAML frontmatter가 있는 `SKILL.md` 파일이 필요합니다:

```markdown
---
name: pdf-processing
description: PDF 파일에서 텍스트와 테이블 추출, 양식 작성, 문서 병합. PDF 파일 작업 시 또는 사용자가 PDF, 양식, 문서 추출을 언급할 때 사용.
---

# PDF Processing

## Quick start

pdfplumber를 사용한 텍스트 추출:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## 고급 기능

**양식 작성**: 전체 가이드는 [FORMS.md](FORMS.md) 참조
**API 레퍼런스**: 모든 메서드는 [REFERENCE.md](REFERENCE.md) 참조
```

### YAML Frontmatter 요구사항

**필수 필드**:
- `name`: Skill 이름 (최대 64자)
- `description`: 간단한 설명 (최대 1024자)

**지원되는 필드는 이 두 개뿐**입니다.

### 명명 규칙 (Naming Conventions)

#### ✅ 좋은 이름 (동사-명사 또는 명사-명사)
```
processing-pdfs
analyzing-spreadsheets
managing-databases
testing-code
writing-documentation
pdf-processing
spreadsheet-analysis
```

#### ❌ 나쁜 이름 (동사형, 너무 일반적)
```
process-pdfs        # 동사형 (동사-명사 OK, 동사만은 X)
analyze-spreadsheets  # 동사형
helper              # 너무 일반적
utils               # 너무 일반적
tools               # 너무 일반적
documents           # 너무 모호
data                # 너무 모호
anthropic-helper    # 불필요한 접두사
claude-tools        # 불필요한 접두사
```

### 효과적인 Description 작성

**구조**: `[기능 설명]. Use when [트리거 조건].`

#### ✅ 좋은 예
```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

```yaml
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.
```

```yaml
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

#### ❌ 나쁜 예 (모호하고 불충분)
```yaml
description: Helps with documents
description: Processes data
description: Does stuff with files
```

**원칙**:
1. **무엇을** 하는지 명확히
2. **언제** 사용해야 하는지 명시
3. **키워드** 포함 (PDF, Excel, commit 등)

---

## 작성 베스트 프랙티스

### 1. 시간 민감 정보 피하기

#### ❌ 나쁜 예
```markdown
2025년 8월 이전이면 구 API를 사용하세요.
2025년 8월 이후면 신 API를 사용하세요.
```

#### ✅ 좋은 예
```markdown
## 현재 방법

v2 API 엔드포인트 사용: `api.example.com/v2/messages`

## 구 패턴

<details>
<summary>레거시 v1 API (2025-08 deprecated)</summary>

v1 API는 `api.example.com/v1/messages` 사용

이 엔드포인트는 더 이상 지원되지 않습니다.
</details>
```

### 2. 일관된 용어 사용

프로젝트 전체에서 동일한 용어를 사용하세요:
- "API key" vs "authentication token"
- "user" vs "customer" vs "client"
- "analyze" vs "process" vs "parse"

하나를 선택하고 일관되게 사용하세요.

### 3. Windows 스타일 경로 피하기

#### ✅ 올바른 경로 (Unix 스타일)
```markdown
scripts/helper.py
reference/guide.md
```

#### ❌ 잘못된 경로 (Windows 스타일)
```markdown
scripts\helper.py
reference\guide.md
```

**이유**: Skills는 Unix 기반 VM에서 실행됩니다.

### 4. 너무 많은 옵션 제공하지 않기

#### ❌ 나쁜 예 (선택 과부하)
```markdown
pypdf, pdfplumber, PyMuPDF, pdf2image, camelot, tabula-py 중 하나를 사용하세요...
```

#### ✅ 좋은 예 (기본값 + 대안)
```markdown
텍스트 추출에는 pdfplumber를 사용하세요:

```python
import pdfplumber
```

OCR이 필요한 스캔 PDF의 경우 pdf2image + pytesseract를 대신 사용하세요.
```

**원칙**: 기본 솔루션 하나 제공 + 특수한 경우 대안

---

## Progressive Disclosure 패턴

### 패턴 1: 고수준 가이드 + 참조

```markdown
---
name: pdf-processing
description: PDF에서 텍스트/테이블 추출, 양식 작성, 문서 병합. PDF 작업 시 사용.
---

# PDF Processing

## Quick start

pdfplumber로 텍스트 추출:

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## 고급 기능

**양식 작성**: 전체 가이드는 [FORMS.md](FORMS.md) 참조
**API 레퍼런스**: 모든 메서드는 [REFERENCE.md](REFERENCE.md) 참조
**예제**: 일반 패턴은 [EXAMPLES.md](EXAMPLES.md) 참조
```

### 패턴 2: 도메인별 조직

```
bigquery-skill/
├── SKILL.md (개요 및 네비게이션)
└── reference/
    ├── finance.md (매출, 청구 메트릭)
    ├── sales.md (기회, 파이프라인)
    ├── product.md (API 사용, 기능)
    └── marketing.md (캠페인, 어트리뷰션)
```

```markdown
# BigQuery 데이터 분석

## 사용 가능한 데이터셋

**Finance**: 매출, ARR, 청구 → [reference/finance.md](reference/finance.md) 참조
**Sales**: 기회, 파이프라인, 계정 → [reference/sales.md](reference/sales.md) 참조
**Product**: API 사용, 기능, 채택 → [reference/product.md](reference/product.md) 참조
**Marketing**: 캠페인, 어트리뷰션 → [reference/marketing.md](reference/marketing.md) 참조

## 빠른 검색

특정 메트릭 찾기:

```bash
grep -i "revenue" reference/finance.md
grep -i "pipeline" reference/sales.md
```
```

### 패턴 3: 조건부 세부사항

```markdown
# DOCX Processing

## 문서 생성

새 문서에는 docx-js 사용. [DOCX-JS.md](DOCX-JS.md) 참조.

## 문서 편집

간단한 편집은 XML 직접 수정.

**추적 변경**: [REDLINING.md](REDLINING.md) 참조
**OOXML 세부사항**: [OOXML.md](OOXML.md) 참조
```

### 주의사항: 깊은 중첩 참조 피하기

#### ❌ 나쁜 예 (3단계 중첩)
```
# SKILL.md
[advanced.md](advanced.md) 참조...

# advanced.md
[details.md](details.md) 참조...

# details.md
실제 정보는 여기에...
```

#### ✅ 좋은 예 (1-2단계)
```markdown
# SKILL.md

**기본 사용법**: [SKILL.md 내 지침]
**고급 기능**: [advanced.md](advanced.md) 참조
**API 레퍼런스**: [reference.md](reference.md) 참조
**예제**: [examples.md](examples.md) 참조
```

### 긴 참조 파일에는 목차 추가

```markdown
# API Reference

## 목차
- 인증 및 설정
- 핵심 메서드 (create, read, update, delete)
- 고급 기능 (배치 작업, 웹훅)
- 에러 핸들링 패턴
- 코드 예제

## 인증 및 설정
...

## 핵심 메서드
...
```

---

## 워크플로우 설계

### 복잡한 작업에는 워크플로우 사용

#### 체크리스트 패턴

```markdown
## PDF 양식 작성 워크플로우

다음 체크리스트를 복사하고 진행 상황을 추적하세요:

```
작업 진행:
- [ ] Step 1: 양식 분석 (analyze_form.py 실행)
- [ ] Step 2: 필드 매핑 생성 (fields.json 편집)
- [ ] Step 3: 매핑 검증 (validate_fields.py 실행)
- [ ] Step 4: 양식 작성 (fill_form.py 실행)
- [ ] Step 5: 출력 확인 (verify_output.py 실행)
```

**Step 1: 양식 분석**

실행: `python scripts/analyze_form.py input.pdf`

양식 필드와 위치를 추출하여 `fields.json`에 저장합니다.

**Step 2: 필드 매핑 생성**

`fields.json`을 편집하여 각 필드에 값을 추가합니다.

**Step 3: 매핑 검증**

실행: `python scripts/validate_fields.py fields.json`

계속하기 전에 검증 오류를 수정하세요.

**Step 4: 양식 작성**

실행: `python scripts/fill_form.py input.pdf fields.json output.pdf`

**Step 5: 출력 확인**

실행: `python scripts/verify_output.py output.pdf`

검증 실패 시 Step 2로 돌아갑니다.
```

### 피드백 루프 구현

```markdown
## 문서 편집 프로세스

1. `word/document.xml` 편집
2. **즉시 검증**: `python ooxml/scripts/validate.py unpacked_dir/`
3. 검증 실패 시:
   - 에러 메시지를 주의 깊게 검토
   - XML에서 문제 수정
   - 검증 다시 실행
4. **검증 통과 시에만 진행**
5. 재빌드: `python ooxml/scripts/pack.py unpacked_dir/ output.docx`
6. 출력 문서 테스트
```

**원칙**: 각 단계 후 검증하고, 실패 시 명확한 되돌아갈 지점 제공

---

## 실행 가능한 코드 포함

### 1. 해결하세요, 떠넘기지 마세요 (Solve, Don't Punt)

#### ✅ 좋은 예 (대안 제공)
```python
def process_file(path):
    """파일 처리, 존재하지 않으면 생성."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        # 실패하는 대신 기본 콘텐츠로 파일 생성
        print(f"File {path} not found, creating default")
        with open(path, 'w') as f:
            f.write('')
        return ''
    except PermissionError:
        # 실패하는 대신 대안 제공
        print(f"Cannot access {path}, using default")
        return ''
```

#### ❌ 나쁜 예 (Claude에게 떠넘김)
```python
def process_file(path):
    # 그냥 실패하고 Claude가 알아서 하도록
    return open(path).read()
```

### 2. 매직 넘버에 주석 달기

#### ✅ 좋은 예
```python
# HTTP 요청은 일반적으로 30초 내 완료
# 긴 타임아웃은 느린 연결을 고려
REQUEST_TIMEOUT = 30

# 3번 재시도가 신뢰성과 속도 균형
# 대부분의 간헐적 실패는 두 번째 재시도에서 해결
MAX_RETRIES = 3
```

#### ❌ 나쁜 예
```python
TIMEOUT = 47  # 왜 47?
RETRIES = 5   # 왜 5?
```

### 3. 유틸리티 스크립트 제공

```markdown
## 유틸리티 스크립트

**analyze_form.py**: PDF에서 모든 양식 필드 추출

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

출력 형식:
```json
{
  "field_name": {"type": "text", "x": 100, "y": 200},
  "signature": {"type": "sig", "x": 150, "y": 500}
}
```

**validate_boxes.py**: 겹치는 경계 상자 확인

```bash
python scripts/validate_boxes.py fields.json
# 반환: "OK" 또는 충돌 목록
```

**fill_form.py**: PDF에 필드 값 적용

```bash
python scripts/fill_form.py input.pdf fields.json output.pdf
```
```

### 4. 시각적 분석 사용

```markdown
## 양식 레이아웃 분석

1. PDF를 이미지로 변환:
   ```bash
   python scripts/pdf_to_images.py form.pdf
   ```

2. 각 페이지 이미지를 분석하여 양식 필드 식별
3. Claude는 필드 위치와 유형을 시각적으로 볼 수 있음
```

### 5. 검증 가능한 중간 출력 생성

```markdown
## 문서 변경 워크플로우

1. 변경사항을 `changes.json`에 기록:
   ```json
   {
     "page": 1,
     "section": "introduction",
     "change": "Added new paragraph about..."
   }
   ```

2. 변경사항 검증:
   ```bash
   python scripts/validate_changes.py changes.json
   ```

3. 검증 통과 시 적용:
   ```bash
   python scripts/apply_changes.py document.xml changes.json
   ```
```

---

## 안티패턴

### 1. ❌ 설치 가정하지 않기

#### 나쁜 예
```markdown
pdf 라이브러리를 사용하여 파일을 처리하세요.
```

#### 좋은 예
```markdown
필요한 패키지 설치: `pip install pypdf`

그 다음 사용:
```python
from pypdf import PdfReader
reader = PdfReader("file.pdf")
```
```

### 2. ❌ MCP 도구 이름을 서버 이름으로 가정하지 않기

#### 나쁜 예
```markdown
`BigQuery` 도구를 사용하세요.
`GitHub` 도구를 사용하세요.
```

#### 좋은 예
```markdown
`BigQuery:bigquery_schema` 도구를 사용하여 테이블 스키마를 검색하세요.
`GitHub:create_issue` 도구를 사용하여 이슈를 생성하세요.
```

**형식**: `ServerName:tool_name`

### 3. ❌ 템플릿에 자유도 제공하지 않기

#### 나쁜 예 (너무 경직됨)
```markdown
## 보고서 구조

**항상** 정확히 이 템플릿 구조를 사용하세요:

```markdown
# [분석 제목]

## 요약
[핵심 발견사항 한 단락 개요]

## 주요 발견사항
- 데이터를 지원하는 발견사항 1
- 데이터를 지원하는 발견사항 2
```
```

#### 좋은 예 (합리적 기본값 + 유연성)
```markdown
## 보고서 구조

다음은 합리적인 기본 형식이지만, 분석에 따라 판단하여 사용하세요:

```markdown
# [분석 제목]

## 요약
[개요]

## 주요 발견사항
[발견한 내용에 따라 섹션 조정]

## 권장사항
[특정 맥락에 맞춤]
```

특정 분석 유형에 따라 필요에 따라 섹션을 조정하세요.
```

---

## 체크리스트

### 핵심 품질

- [ ] **간결함**: 불필요한 설명 없이 실행 가능한 지침만
- [ ] **명확한 트리거**: description이 언제 사용할지 명확히 명시
- [ ] **일관된 용어**: 동일한 개념에 동일한 단어 사용
- [ ] **Unix 경로**: 모든 파일 경로가 슬래시(/) 사용
- [ ] **시간 독립적**: 날짜나 시간 참조 없음
- [ ] **모델 테스트**: 사용할 모든 Claude 모델에서 테스트 완료

### Skill 구조

- [ ] **YAML frontmatter**: `name`과 `description` 필드 포함
- [ ] **Character limits**: name ≤ 64자, description ≤ 1024자
- [ ] **Progressive disclosure**: 추가 참조 파일은 필요 시에만 링크
- [ ] **목차**: 긴 파일(>500줄)에 목차 포함
- [ ] **1-2 단계 참조**: 3단계 이상 중첩 피하기

### 워크플로우

- [ ] **체크리스트**: 복잡한 작업에 복사 가능한 체크리스트 제공
- [ ] **명확한 단계**: 각 단계가 명확하고 실행 가능
- [ ] **피드백 루프**: 검증 단계와 실패 시 되돌아갈 지점 명시
- [ ] **조건부 분기**: "if X, do Y" 패턴 명확히

### 코드와 스크립트

- [ ] **대안 제공**: 스크립트가 일반적 실패 케이스 처리
- [ ] **매직 넘버 주석**: 하드코딩된 값에 이유 설명
- [ ] **명확한 출력**: 스크립트 출력 형식 문서화
- [ ] **의존성 명시**: 필요한 패키지와 설치 방법 명시
- [ ] **시각적 분석**: 필요 시 이미지 변환 도구 제공

### 테스트

- [ ] **평가 케이스**: 최소 3-5개의 대표 테스트 케이스
- [ ] **성공 기준**: 각 케이스의 예상 동작 정의
- [ ] **실패 케이스**: 일반적 실패 시나리오 테스트
- [ ] **에지 케이스**: 경계 조건 테스트
- [ ] **반복 개선**: Claude 사용 패턴 관찰하고 개선

---

## 일반 패턴 라이브러리

### 템플릿 패턴

```markdown
## 커밋 메시지 형식

다음 예제에 따라 커밋 메시지 생성:

**Example 1:**
Input: JWT 토큰으로 사용자 인증 추가
Output:
```
feat(auth): JWT 기반 인증 구현

로그인 엔드포인트와 토큰 검증 미들웨어 추가
```

**Example 2:**
Input: 보고서에 날짜가 잘못 표시되는 버그 수정
Output:
```
fix(reports): 시간대 변환에서 날짜 형식 수정

보고서 생성 전체에서 일관되게 UTC 타임스탬프 사용
```

이 스타일을 따르세요: type(scope): 간단한 설명, 그 다음 상세 설명.
```

### 조건부 워크플로우 패턴

```markdown
## 문서 수정 워크플로우

1. 수정 유형 결정:

   **새 콘텐츠 생성?** → 아래 "생성 워크플로우" 따르기
   **기존 콘텐츠 편집?** → 아래 "편집 워크플로우" 따르기

2. 생성 워크플로우:
   - docx-js 라이브러리 사용
   - 처음부터 문서 빌드
   - .docx 형식으로 내보내기

3. 편집 워크플로우:
   - 기존 문서 압축 해제
   - XML 직접 수정
   - 각 변경 후 검증
   - 완료 시 재압축
```

---

## 참고 자료

### 공식 문서
- [Agent Skills Overview](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)
- [Best Practices](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [Quickstart](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/quickstart)
- [Use Skills with the Claude API](https://docs.anthropic.com/en/api/skills-guide)
- [Use Skills in Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)

### 예제
- [Skills Cookbook (GitHub)](https://github.com/anthropics/claude-cookbooks/tree/main/skills)

### 블로그
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

---

## 변경 이력

- **2025-10-28**: 초기 버전 작성 (Anthropic 공식 문서 기반)
