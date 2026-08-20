# 컨테이너 없이 SQLite로 LoCoMo 실행하기

*[English](LOCOMO_SQLITE.md)*

SQLite 파일만 저장소로 쓰는 MemMachine 서버를 대상으로 LoCoMo 전 과정
(ingest, search, judge, score)을 실행하는 방법입니다. 모델은 로컬 Ollama가
제공합니다. Neo4j도, Postgres도, Docker도, OpenAI 계정도 필요 없습니다.

벤치마크의 REST 변형(`restapiv2_locomo_ingest.py`,
`restapiv2_locomo_search.py`)을 사용합니다. 이 스크립트들은 실행 중인 서버에
HTTP로 접속하므로 서버가 지원하는 어떤 백엔드에서도 동작합니다. 같은
디렉터리의 in-process 변형([README.md](README.md)에 문서화)은 라이브러리를
직접 임포트하고 VectorGraphStore를 요구해서 여전히 Neo4j가 있어야 합니다.

## 사전 준비

- [uv](https://docs.astral.sh/uv/)
- 로컬에서 실행 중인 [Ollama](https://ollama.com/)와 모델 세 개:

```sh
ollama pull nomic-embed-text   # 임베딩
ollama pull llama3             # 답변 생성
ollama pull llama3.3           # LLM judge, "judge 모델 선택" 절 참고
```

`locomo10.json`은 `evaluation/data/`에 이미 커밋돼 있어 내려받을 것이
없습니다.

아래 명령은 다음 경로를 가정합니다.

```sh
REPO=~/work/ltm/MemMachine
RUN="uv run --project $REPO --frozen --all-extras"
WORK=~/locomo-run
mkdir -p $WORK
```

## 1단계: 서버 기동

```sh
cd $REPO
./dev-sqlite.sh start
```

`sample_configs/episodic_memory_config.sqlite.sample`을 작업 디렉터리로
복사하고, bm25 reranker가 쓰는 NLTK stopwords를 내려받고, 서버를 띄운 뒤
healthy가 될 때까지 기다립니다. 직접 하려면:

```sh
mkdir -p $WORK/server && cd $WORK/server
cp $REPO/sample_configs/episodic_memory_config.sqlite.sample configuration.yml
$RUN memmachine-nltk-setup                      # 최초 1회
MEMORY_CONFIG=$PWD/configuration.yml HOST=127.0.0.1 PORT=8080 \
  $RUN memmachine-server
```

**포트는 8080이어야 합니다.** `MemmachineHelperRestapiv2`가
`http://localhost:8080`을 기본값으로 쓰는데 이를 바꿀 플래그가 없습니다.

## 2단계: ingest

```sh
cd $WORK          # 메트릭 파일이 현재 디렉터리에 쌓입니다
$RUN python $REPO/evaluation/episodic_memory/restapiv2_locomo_ingest.py \
  --data-path $REPO/evaluation/data/locomo10.json \
  --conv-start 1 --conv-stop 1 --batch-size 10
```

`--conv-start` / `--conv-stop`으로 대화를 선택합니다. 데이터셋에는 10개가
들어 있습니다. 여기서는 모델 환경변수가 필요 없습니다. 임베딩은 서버가
`configuration.yml`에 따라 처리합니다.

## 3단계: search

```sh
cd $WORK
OPENAI_API_KEY=ollama \
OPENAI_API_BASE=http://localhost:11434/v1 \
OPENAI_MODEL_NAME=llama3 \
$RUN python $REPO/evaluation/episodic_memory/restapiv2_locomo_search.py \
  --data-path $REPO/evaluation/data/locomo10.json \
  --target-path $WORK/locomo_result.json \
  --conv-start 1 --conv-stop 1 --top-k 20 --max-workers 4
```

환경변수는 **답변을 작성하는 모델**을 지정합니다. `--conv-start` /
`--conv-stop`은 2단계와 같은 범위로 맞추세요.

## 4단계: judge

```sh
cd $REPO/evaluation/episodic_memory
OPENAI_API_KEY=ollama \
OPENAI_API_BASE=http://localhost:11434/v1 \
OPENAI_MODEL_NAME=llama3.3 \
$RUN python locomo_evaluate.py \
  --data-path $WORK/locomo_result.json \
  --target-path $WORK/evaluation_metrics.json
```

주의할 점 두 가지:

- **`evaluation/episodic_memory/`에서 실행해야 합니다.**
  `locomo_evaluate.py`가 `from llm_judge import evaluate_llm_judge`로
  임포트하기 때문에, 다른 위치에서 절대경로로 호출하면
  `ModuleNotFoundError`가 납니다.
- **`--data-path`는 데이터셋이 아니라 3단계의 결과 파일입니다.**

## 5단계: 점수 집계

`generate_scores.py`는 현재 디렉터리의 `evaluation_metrics.json`을 읽습니다.
4단계에서 그 이름으로 저장한 이유입니다.

```sh
cd $WORK
$RUN python $REPO/evaluation/episodic_memory/generate_scores.py
```

## 6단계: 정리

```sh
cd $REPO
./dev-sqlite.sh stop     # reset 을 쓰면 SQLite 파일까지 삭제됩니다
```

## 실제 실행 기록

대화 1개(`--conv-start 1 --conv-stop 1`), 152문항, 16코어 CPU 전용 머신,
RAM 38GiB. 모든 모델은 Ollama가 서빙했습니다.

```
Mean Scores Per Category:
          llm_score  count
category
1            0.6875     32
2            0.5676     37
3            0.7692     13
4            0.8857     70

Overall Mean Scores:
llm_score    0.7566
```

카테고리는 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop입니다.
single-hop이 가장 높고 temporal이 가장 낮으며 multi-hop이 그 사이인,
예상대로의 순서입니다.

| 단계 | 소요 시간 |
| --- | --- |
| Ingest | 15초 |
| Search | 20분 53초 |
| Judge | 28분 40초 |
| 합계 | 약 50분 |

**저장소는 병목이 아니었습니다.** ingest는 임베딩 22,141 토큰 생성을 포함해
15초 만에 끝났고, 두 SQLite 파일을 260KB에서 8.2MB로 키웠습니다. search는
문항당 평균 8.2초, judge는 문항당 평균 11.3초가 걸렸는데 둘 다 모델 추론
시간입니다. judge가 가장 느린 이유는 `locomo_evaluate.py`가 순차로 도는
반면 search는 `--max-workers`를 받기 때문입니다.

search는 문항당 5,000~7,000건의 메모리를 조회했지만 SQLite가 시간에
드러나지 않았습니다. 다만 이것은 대화 1개 기준입니다. 10개를 돌리면 벡터
인덱스가 10배가 되므로, 같은 결과를 가정하기 전에 별도 측정이 필요합니다.

## semantic memory는 꺼져 있습니다

샘플은 `semantic_memory.enabled: false`로 설정합니다. semantic memory는
저장된 메시지에서 프로필 피처를 뽑아내려고 백그라운드에서 언어 모델을
호출하는데, 켜져 있다는 걸 알아차리기 어렵습니다. LoCoMo 대화 하나를
ingest했더니 약 1,200건이 대기열에 쌓였고, 벤치마크가 끝난 뒤에도 몇 시간
동안 GPU를 점유했습니다.

프로필 피처가 작업 대상일 때만 켜시고, 그 전에 모델 컨텍스트를 충분히
확보하세요. 추출 프롬프트는 누적된 프로필 전체를 함께 보내기 때문에 프로필이
커질수록 길어지는데, Ollama는 별도 지정이 없으면 `num_ctx` 4096으로
서빙합니다.

```
openai.LengthFinishReasonError: Could not parse response content as the length
limit was reached - CompletionUsage(prompt_tokens=3926, completion_tokens=170,
total_tokens=4096)
```

이렇게 실패한 메시지는 ingested로 표시되지 않고 purge 대상에서도 빠지므로,
루프가 약 1분마다 영원히 재시도합니다. 컨텍스트를 32768로 올리자 에러가
사라지고 대기열이 줄기 시작했습니다.

## judge 모델 선택

채점은 답변 생성보다 어려운 작업입니다. 너무 작은 모델은 실패하는 대신
**모든 답에 동의해버려서**, 아무 의미 없는 높은 점수를 만들어냅니다. 정답이
"mental health"인 질문에 "It raised awareness for ocean plastic pollution"을
채점시켜 본 결과입니다.

| 모델 | 정답 케이스 | 오답 케이스 | "May 7th" vs "7 May 2023" |
| --- | --- | --- | --- |
| `llama3` | CORRECT | **CORRECT** | - |
| `llama3.3` | CORRECT | WRONG | CORRECT |
| `qwen3.5` | 파싱 실패 | | |

`llama3`를 썼다면 무엇을 검색하든 만점에 가까운 점수가 나왔을 것입니다.
`qwen3.5`는 응답이 `json_repair.loads()`를 통과하지 못하고 라벨을 읽기 전에
`TypeError`를 냅니다. `llama3.3` 또는 그에 준하는 모델을 쓰세요.

## 이 수치를 어떻게 보면 안 되는가

**MemMachine의 성능 지표가 아닙니다.** 10개 중 대화 1개만 사용했고, 답변에
`llama3`, 채점에 `llama3.3`을 썼으며(통상 `gpt-4o-mini`), `--top-k`도 기본
50이 아닌 20이었습니다. **SQLite에서 파이프라인이 끝까지 동작하고 합리적인
수치를 낸다**는 근거로만 보시고, 비교는 동일 조건에서 실행한 결과끼리만
하세요.
