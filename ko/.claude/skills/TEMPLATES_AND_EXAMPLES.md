# Claude Skills 실전 템플릿 모음

## 목차

1. [기본 Skill 템플릿](#기본-skill-템플릿)
2. [Progressive Disclosure 예제](#progressive-disclosure-예제)
3. [워크플로우 예제](#워크플로우-예제)
4. [코드 포함 예제](#코드-포함-예제)
5. [도메인별 예제](#도메인별-예제)

---

## 기본 Skill 템플릿

### 템플릿 1: 단순 Skill (한 파일)

```markdown
---
name: simple-task
description: [무엇을 하는지]. Use when [언제 사용하는지].
---

# Simple Task

## Quick start

[가장 일반적인 사용 사례를 위한 최소 예제]

```python
# 핵심 코드
```

## 일반적인 변형

**Case 1**: [설명] → [해결책]
**Case 2**: [설명] → [해결책]

## 문제 해결

**Error X**: [원인] → [해결책]
**Error Y**: [원인] → [해결책]
```

**사용 예시**:
```markdown
---
name: json-validation
description: Validate and format JSON files, fixing common syntax errors. Use when working with JSON files or when user mentions JSON validation, formatting, or syntax errors.
---

# JSON Validation

## Quick start

기본 검증:

```python
import json

with open('data.json') as f:
    try:
        data = json.load(f)
        print("✓ Valid JSON")
    except json.JSONDecodeError as e:
        print(f"✗ Error at line {e.lineno}: {e.msg}")
```

## 일반적인 문제

**Trailing commas**: JSON에서 허용되지 않음 → 마지막 쉼표 제거
**Single quotes**: 허용되지 않음 → 큰따옴표로 변경
**Unquoted keys**: 허용되지 않음 → 키를 따옴표로 감싸기

## 자동 수정

```python
import json5  # JSON5 파서 설치: pip install json5

with open('broken.json') as f:
    data = json5.load(f)  # 느슨한 구문 허용

# 표준 JSON으로 저장
with open('fixed.json', 'w') as f:
    json.dump(data, f, indent=2)
```
```

---

## Progressive Disclosure 예제

### 예제 1: 문서 처리 Skill

**디렉토리 구조**:
```
docx-skill/
├── SKILL.md                    # 메인 가이드 (항상 로드)
├── ADVANCED.md                 # 고급 기능 (필요 시)
├── REDLINING.md                # 추적 변경 (필요 시)
├── OOXML.md                    # 기술 참조 (필요 시)
└── scripts/
    ├── validate.py             # 검증 스크립트
    └── pack.py                 # 패킹 스크립트
```

**SKILL.md** (메인):
```markdown
---
name: docx-processing
description: Create and edit Word documents (.docx), including tracked changes and comments. Use when working with Word documents or when user mentions .docx, document editing, or tracked changes.
---

# DOCX Processing

## 새 문서 생성

python-docx 사용:

```python
from docx import Document

doc = Document()
doc.add_heading('Document Title', 0)
doc.add_paragraph('Hello World')
doc.save('output.docx')
```

## 기존 문서 편집

간단한 텍스트 변경은 python-docx로:

```python
doc = Document('existing.docx')
doc.paragraphs[0].text = 'New text'
doc.save('modified.docx')
```

**복잡한 편집이 필요한 경우**:
- **추적 변경 (Track Changes)**: [REDLINING.md](REDLINING.md) 참조
- **고급 서식**: [ADVANCED.md](ADVANCED.md) 참조
- **OOXML 수정**: [OOXML.md](OOXML.md) 참조

## 문서 검증

항상 편집 후 검증:

```bash
python scripts/validate.py document.docx
```
```

**REDLINING.md** (필요 시 로드):
```markdown
# 추적 변경 (Track Changes) 가이드

## 개요

Word의 추적 변경 기능은 OOXML의 `<w:ins>`, `<w:del>` 태그로 구현됩니다.

## 워크플로우

1. **문서 압축 해제**:
   ```bash
   unzip document.docx -d unpacked/
   ```

2. **XML 수정**:
   ```xml
   <!-- 텍스트 삽입 -->
   <w:ins w:id="1" w:author="Claude" w:date="2025-10-28T00:00:00Z">
     <w:r><w:t>새 텍스트</w:t></w:r>
   </w:ins>

   <!-- 텍스트 삭제 -->
   <w:del w:id="2" w:author="Claude" w:date="2025-10-28T00:00:00Z">
     <w:r><w:delText>구 텍스트</w:delText></w:r>
   </w:del>
   ```

3. **검증 및 재압축**:
   ```bash
   python scripts/validate.py unpacked/
   python scripts/pack.py unpacked/ output.docx
   ```

## 전체 예제는 [EXAMPLES.md](EXAMPLES.md) 참조
```

---

### 예제 2: 데이터 분석 Skill (도메인별)

**디렉토리 구조**:
```
bigquery-skill/
├── SKILL.md                    # 개요 및 네비게이션
└── reference/
    ├── finance.md              # 재무 스키마
    ├── sales.md                # 영업 스키마
    ├── product.md              # 제품 스키마
    └── marketing.md            # 마케팅 스키마
```

**SKILL.md**:
```markdown
---
name: bigquery-analytics
description: Query and analyze company data from BigQuery across finance, sales, product, and marketing datasets. Use when analyzing business metrics, revenue, pipeline, or campaign data.
---

# BigQuery Analytics

## 사용 가능한 데이터셋

| 도메인 | 주요 메트릭 | 스키마 참조 |
|--------|-------------|-------------|
| **Finance** | 매출, ARR, 청구 | [reference/finance.md](reference/finance.md) |
| **Sales** | 기회, 파이프라인 | [reference/sales.md](reference/sales.md) |
| **Product** | API 사용, 기능 | [reference/product.md](reference/product.md) |
| **Marketing** | 캠페인, 전환 | [reference/marketing.md](reference/marketing.md) |

## 빠른 검색

특정 메트릭 찾기:

```bash
# 매출 관련 테이블 찾기
grep -i "revenue" reference/finance.md

# 파이프라인 관련 테이블 찾기
grep -i "pipeline" reference/sales.md
```

## 쿼리 템플릿

**월별 매출**:
```sql
SELECT
  DATE_TRUNC(date, MONTH) as month,
  SUM(amount) as revenue
FROM finance.transactions
GROUP BY month
ORDER BY month DESC
```

자세한 스키마는 해당 도메인 참조 파일을 확인하세요.
```

**reference/finance.md**:
```markdown
# Finance 데이터 스키마

## finance.transactions

월별 거래 데이터

| 컬럼 | 타입 | 설명 |
|------|------|------|
| transaction_id | STRING | 고유 거래 ID |
| date | DATE | 거래 날짜 |
| customer_id | STRING | 고객 ID |
| amount | FLOAT64 | 거래 금액 (USD) |
| type | STRING | 'revenue', 'refund', 'chargeback' |
| subscription_id | STRING | 구독 ID (해당 시) |

## finance.arr

Annual Recurring Revenue

| 컬럼 | 타입 | 설명 |
|------|------|------|
| date | DATE | 스냅샷 날짜 |
| arr | FLOAT64 | 총 ARR (USD) |
| new_arr | FLOAT64 | 신규 ARR |
| expansion_arr | FLOAT64 | 확장 ARR |
| churn_arr | FLOAT64 | 이탈 ARR |

## 일반적인 쿼리

**분기별 ARR 성장**:
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

## 워크플로우 예제

### 예제 1: 체크리스트 기반 워크플로우

```markdown
---
name: code-review-workflow
description: Conduct thorough code reviews with checklist-based approach. Use when reviewing code, pull requests, or when user asks for code review.
---

# Code Review Workflow

## 리뷰 프로세스

다음 체크리스트를 복사하고 각 항목을 확인하세요:

```
코드 리뷰 진행:
- [ ] 1단계: 코드 구조 분석
- [ ] 2단계: 기능 정확성 검증
- [ ] 3단계: 엣지 케이스 확인
- [ ] 4단계: 성능 검토
- [ ] 5단계: 보안 취약점 점검
- [ ] 6단계: 테스트 커버리지 확인
- [ ] 7단계: 문서화 검토
- [ ] 8단계: 종합 피드백 작성
```

### 1단계: 코드 구조 분석

**확인 사항**:
- [ ] 함수/클래스 책임이 명확한가?
- [ ] 적절한 추상화 레벨인가?
- [ ] 네이밍이 일관되고 명확한가?
- [ ] 중복 코드가 있는가?

**피드백 형식**:
```
## 구조
✓ 명확한 관심사 분리
⚠ UserService의 책임이 너무 많음 → 분리 제안
```

### 2단계: 기능 정확성 검증

**확인 사항**:
- [ ] 요구사항을 모두 구현했는가?
- [ ] 로직이 올바른가?
- [ ] 예상 입력에 대해 올바른 출력을 생성하는가?

**피드백 형식**:
```
## 기능
✓ 기본 플로우 정확
✗ 빈 배열 입력 시 크래시 → null 체크 추가 필요
```

### 3-8단계는 유사한 패턴...

## 최종 리포트 템플릿

```markdown
# 코드 리뷰: [PR 제목]

## 요약
- **상태**: 승인 / 변경 요청 / 코멘트
- **주요 발견사항**: [한 문장 요약]

## 긍정적 측면
- [잘된 점 1]
- [잘된 점 2]

## 개선 필요 사항
### 🔴 Critical (머지 전 필수 수정)
- [심각한 문제]

### 🟡 Important (다음 PR에서 수정)
- [중요하지만 블로커는 아닌 문제]

### 🟢 Nice to have (선택적)
- [사소한 개선 제안]

## 상세 코멘트
[각 파일/함수별 상세 피드백]
```
```

### 예제 2: 피드백 루프 워크플로우

```markdown
---
name: api-integration-workflow
description: Integrate external APIs with validation and error handling workflow. Use when integrating third-party APIs or external services.
---

# API Integration Workflow

## 통합 프로세스

### Phase 1: 스펙 확인

1. API 문서 읽기
2. 인증 방식 확인 (API key, OAuth, etc.)
3. Rate limits 확인
4. 테스트 엔드포인트 확인

**검증**: API 문서 URL과 인증 정보가 준비되었는가?
- Yes → Phase 2로
- No → 문서 수집 후 다시 시작

### Phase 2: 연결 테스트

```python
import requests

# 테스트 요청
response = requests.get(
    'https://api.example.com/health',
    headers={'Authorization': f'Bearer {API_KEY}'}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

**검증**: 200 응답을 받았는가?
- Yes → Phase 3으로
- No → 인증 정보 확인 후 Phase 2 반복

### Phase 3: 기본 기능 구현

```python
def get_data(endpoint, params=None):
    """API 호출 공통 함수"""
    response = requests.get(
        f'{BASE_URL}/{endpoint}',
        headers=headers,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

**검증**: 실제 데이터를 가져올 수 있는가?
- Yes → Phase 4로
- No → 에러 로그 확인 후 Phase 3 반복

### Phase 4: 에러 핸들링

```python
from requests.exceptions import RequestException, Timeout

def safe_api_call(endpoint, params=None, retries=3):
    """재시도 로직이 있는 안전한 API 호출"""
    for attempt in range(retries):
        try:
            return get_data(endpoint, params)
        except Timeout:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
        except RequestException as e:
            logger.error(f"API error: {e}")
            raise
```

**검증**: 네트워크 오류 시 적절히 처리되는가?
- Yes → Phase 5로
- No → 에러 케이스 추가 후 Phase 4 반복

### Phase 5: 테스트 작성

```python
def test_api_integration():
    # 정상 케이스
    data = safe_api_call('users/123')
    assert data['id'] == '123'

    # 에러 케이스
    with pytest.raises(RequestException):
        safe_api_call('invalid/endpoint')

    # 타임아웃
    with pytest.raises(Timeout):
        safe_api_call('slow/endpoint')
```

**검증**: 모든 테스트가 통과하는가?
- Yes → 완료!
- No → 실패한 테스트 수정 후 Phase 5 반복
```

---

## 코드 포함 예제

### 예제 1: 유틸리티 스크립트 포함

**디렉토리 구조**:
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

## 워크플로우

### Step 1: 양식 분석

`analyze_form.py` 스크립트로 양식 필드 추출:

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

**출력 형식**:
```json
{
  "applicant_name": {
    "type": "text",
    "page": 1,
    "x": 100, "y": 200,
    "width": 200, "height": 20
  },
  "signature": {
    "type": "signature",
    "page": 2,
    "x": 150, "y": 500,
    "width": 300, "height": 50
  }
}
```

### Step 2: 값 매핑

`fields.json`을 편집하여 각 필드에 값 추가:

```json
{
  "applicant_name": {
    "type": "text",
    "page": 1,
    "x": 100, "y": 200,
    "width": 200, "height": 20,
    "value": "John Doe"  // 이 줄 추가
  },
  ...
}
```

### Step 3: 검증

`validate_fields.py`로 필드 매핑 검증:

```bash
python scripts/validate_fields.py fields.json
```

**출력**:
- 모든 필수 필드가 채워졌는지 확인
- 겹치는 필드가 있는지 확인
- 값의 형식이 올바른지 확인

### Step 4: 양식 작성

`fill_form.py`로 PDF 생성:

```bash
python scripts/fill_form.py input.pdf fields.json output.pdf
```

## 유틸리티 스크립트 상세

### analyze_form.py

**기능**: PDF에서 모든 입력 가능한 필드 추출

**사용법**:
```bash
python scripts/analyze_form.py <input.pdf> [--output <fields.json>]
```

**옵션**:
- `--output`: 출력 파일 (기본값: stdout)
- `--pages`: 분석할 페이지 범위 (예: 1-3)

### validate_fields.py

**기능**: 필드 매핑 검증 및 문제 탐지

**사용법**:
```bash
python scripts/validate_fields.py <fields.json>
```

**검증 항목**:
1. 필수 필드 확인
2. 타입 일치 확인
3. 좌표 경계 확인
4. 중복 필드 확인

### fill_form.py

**기능**: 매핑에 따라 PDF 양식 작성

**사용법**:
```bash
python scripts/fill_form.py <input.pdf> <fields.json> <output.pdf>
```

**옵션**:
- `--font`: 폰트 이름 (기본값: Helvetica)
- `--font-size`: 폰트 크기 (기본값: 10)
```

**scripts/analyze_form.py**:
```python
#!/usr/bin/env python3
"""PDF 양식 필드 분석 스크립트"""

import sys
import json
from pypdf import PdfReader

def analyze_form(pdf_path):
    """PDF에서 모든 필드 추출"""
    reader = PdfReader(pdf_path)
    fields = {}

    for page_num, page in enumerate(reader.pages, 1):
        if '/Annots' in page:
            for annot in page['/Annots']:
                obj = annot.get_object()
                if obj.get('/FT'):  # 필드 타입
                    field_name = obj.get('/T')
                    field_type = obj.get('/FT')
                    rect = obj.get('/Rect')

                    fields[field_name] = {
                        'type': field_type.replace('/', ''),
                        'page': page_num,
                        'x': float(rect[0]),
                        'y': float(rect[1]),
                        'width': float(rect[2]) - float(rect[0]),
                        'height': float(rect[3]) - float(rect[1])
                    }

    return fields

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_form.py <input.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    fields = analyze_form(pdf_path)
    print(json.dumps(fields, indent=2))
```

---

## 도메인별 예제

### 백엔드 개발

```markdown
---
name: fastapi-crud
description: Build CRUD API endpoints with FastAPI, including validation, error handling, and database integration. Use when creating REST APIs with FastAPI.
---

# FastAPI CRUD Pattern

## 기본 구조

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

app = FastAPI()

# 모델
class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float

class ItemResponse(ItemCreate):
    id: int

    class Config:
        from_attributes = True

# 엔드포인트
@app.post("/items/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

## 상세 패턴은 [PATTERNS.md](PATTERNS.md) 참조
```

### 프론트엔드 개발

```markdown
---
name: react-component-patterns
description: Build React components following best practices with TypeScript, hooks, and proper error handling. Use when creating React components.
---

# React Component Patterns

## 기본 컴포넌트

```typescript
import React, { useState, useEffect } from 'react';

interface UserProps {
  userId: string;
}

export const UserProfile: React.FC<UserProps> = ({ userId }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(res => res.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return <div>User not found</div>;

  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
};
```

## 고급 패턴은 [ADVANCED.md](ADVANCED.md) 참조
```

---

## 빠른 시작 가이드

### 1. 간단한 Skill 만들기 (5분)

```bash
mkdir my-skill
cd my-skill
```

`SKILL.md` 생성:
```markdown
---
name: my-first-skill
description: [무엇을 하는지]. Use when [언제 사용하는지].
---

# My First Skill

## Quick start

[핵심 예제]

```python
# 코드
```
```

### 2. Progressive Disclosure 추가 (10분)

```bash
touch ADVANCED.md
touch REFERENCE.md
```

`SKILL.md` 수정:
```markdown
## 고급 기능

자세한 내용은 다음 참조:
- **고급 사용법**: [ADVANCED.md](ADVANCED.md)
- **API 레퍼런스**: [REFERENCE.md](REFERENCE.md)
```

### 3. 스크립트 추가 (15분)

```bash
mkdir scripts
```

유틸리티 스크립트 작성 및 `SKILL.md`에서 참조

---

## 다음 단계

1. **베스트 프랙티스 문서** 읽기: [CLAUDE_SKILLS_BEST_PRACTICES.md](CLAUDE_SKILLS_BEST_PRACTICES.md)
2. **공식 Cookbook** 참조: https://github.com/anthropics/claude-cookbooks/tree/main/skills
3. **Claude로 테스트**: 실제로 사용해보며 개선
4. **피드백 수집**: Claude가 어떻게 탐색하는지 관찰

---

## 변경 이력

- **2025-10-28**: 초기 버전 작성
