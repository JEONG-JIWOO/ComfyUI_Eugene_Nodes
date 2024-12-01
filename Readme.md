# Eugene's ComfyUI Custom Utility Nodes

ComfyUI 워크플로우를 최적화하고 관리하기 위한 유틸리티 노드 모음입니다.

## Dictionary Based Prompt Management
Python Dictionary를 활용하여 프롬프트 텍스트를 체계적으로 관리하고 재사용할 수 있는 유틸리티 노드들을 제공합니다.

### Core Dictionary Nodes
- DictUpdate1
  - 단일 key-value 쌍을 dictionary에 추가/업데이트
  - 입력 dictionary가 없는 경우 새로운 dictionary 생성
  - 빈 key 또는 value는 무시됨

- DictUpdate5
  - 최대 5개의 key-value 쌍을 동시에 추가/업데이트 
  - 입력 dictionary가 없는 경우 새로운 dictionary 생성
  - 빈 key 또는 value는 자동으로 무시됨
  - 모든 필드는 선택적(optional)으로 사용 가능

- DictUpdate10
  - 최대 10개의 key-value 쌍을 동시에 추가/업데이트
  - 입력 dictionary가 없는 경우 새로운 dictionary 생성
  - 빈 key 또는 value는 자동으로 무시됨
  - 모든 필드는 선택적(optional)으로 사용 가능

### Dictionary Utilities
- DictTemplate
  - Dictionary의 값들을 템플릿 텍스트에 적용
  - 멀티라인 텍스트 지원
  - 문법: {key} 형식으로 placeholder 지정
  - 예시:
    ```python
    dictionary = {"cloth": "shirts and pants"}
    template = "1 man wears {cloth}"
    result = "1 man wears shirts and pants"
    ```

- DictMultilineSelect
  - 멀티라인 텍스트에서 특정 라인을 선택하여 dictionary에 추가
  - 입력:
    - 기존 dictionary
    - 선택할 라인 번호
    - 멀티라인 텍스트
    - 새로운 key 문자열
  - 출력: 업데이트된 dictionary와 선택된 라인 번호

### Dictionary Bus Nodes
Dictionary와 모델 컴포넌트들(MODEL, CLIP, VAE 등)을 함께 관리하기 위한 유틸리티 노드들입니다.

- DictBus
  - Dictionary와 모델 컴포넌트들을 하나의 번들로 묶음
  - 필수 입력: dictionary, model, clip, vae
  - 선택 입력: image, latent
  - 워크플로우에서 여러 컴포넌트를 단일 연결로 전달 가능

- DictBusUnpack
  - DictBus 번들을 개별 컴포넌트로 분리
  - 모든 컴포넌트(dictionary, model, clip, vae, image, latent)를 개별적으로 출력
  - 원본 bus도 함께 출력되어 계속 사용 가능

- DictBusEdit
  - DictBus 번들의 특정 컴포넌트만 선택적으로 수정
  - 수정하지 않은 컴포넌트는 원본 값 유지
  - 워크플로우 중간에 필요한 컴포넌트만 업데이트 가능

## 디렉토리 구조
```
eugene_comfyui_nodes/
├── __init__.py
├── nodes/
│   ├── __init__.py
│   ├── dictionary_nodes.py
│   └── dictionary_bus.py
└── README.md
```