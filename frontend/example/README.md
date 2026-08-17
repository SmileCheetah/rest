# 쉼표 MVP · Phase 5 Figma Import HTML

## 핵심
- 모든 화면은 375×812px 기준입니다.
- Layout은 absolute positioning을 최소화하고 Flex + gap + padding 중심으로 구성했습니다.
- `tokens.css`의 CSS Variables는 Figma Variables로 옮기기 쉽도록 분리했습니다.
- 반복 UI는 동일 class를 재사용합니다:
  - `.button`
  - `.badge`
  - `.ai-rec`
  - `.weather-card`
  - `.visit-card`
  - `.route-card`
  - `.bottom-sheet`
  - `.dialog`
  - `.text-chips`
  - 지도 marker / route 스타일
- 기본 이모지는 사용하지 않았습니다.
- 아이콘은 inline SVG라 HTML→Figma import 후 vector로 다루기 쉽습니다.
- 지도는 외부 API나 raster image가 아닌 SVG mock이라 레이어 편집이 가능합니다.

## 파일
- `index.html` : 전체 화면을 한 보드에 배치
- `tokens.css` : 컬러 / spacing / radius / shadow / typography token
- `styles.css` : 공통 component + 화면 layout
- `screens/*.html` : 개별 화면 파일

## 화면
1. A01 오늘의 방문 일정
2. A01-S01 대상자 추가 Bottom Sheet
3. A01-S02 일정 삭제 Context Menu
4. B01 이동 경로 확인
5. B01-S01 AI 판단 근거 Dialog
6. B01-S02 고위험 일반경로 선택 Confirm
7. B01-S03 쿨링스팟 상세 Bottom Sheet
8. B03 길 안내
9. B03-S01 쉼터 건너뛰기 Bottom Sheet
10. C01 오늘 업무 완료

## Figma import 후 권장 정리
HTML-to-Figma 플러그인이 CSS의 모든 component semantics를 자동으로 Figma Component로 바꾸지는 않습니다.
Import 후 아래 순서로 정리하면 가장 빠릅니다.

1. `tokens.css` 값을 Figma Variables로 등록
   - Brand / Status / Surface / Text / Border
   - Radius
   - Spacing
2. 아래 반복 요소를 Component로 생성
   - Button: Primary / Teal / Secondary / Ghost / Danger
   - Badge: Safe / Caution / Danger / Outline
   - AI Recommendation
   - Visit Card
   - Route Card
   - Bottom Sheet
   - Dialog
   - Text Chip
3. 반복 Frame에 Auto Layout 적용
   - Vertical: Screen content, card, sheet, dialog
   - Horizontal: header, footer, AI recommendation, route cards
4. 개별 화면은 `screens/` HTML로 import하면 375px width가 그대로 유지됩니다.

## 중요한 한계
HTML 구조를 Figma로 가져오는 플러그인은 플러그인마다 Auto Layout / Component 변환 수준이 다릅니다.
이 파일은 변환 성공률을 높이기 위해 CSS Flex 기반으로 구성했지만,
"HTML class가 자동으로 Figma Component가 되는 것"까지는 보장할 수 없습니다.
