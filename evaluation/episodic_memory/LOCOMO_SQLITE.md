# LoCoMo on SQLite, without containers

This walks through a full LoCoMo run - ingest, search, judge, score - against
a MemMachine server backed by SQLite files, with a local Ollama providing the
models. No Neo4j, no Postgres, no Docker, and no OpenAI account.

It uses the REST variant of the benchmark (`restapiv2_locomo_ingest.py` and
`restapiv2_locomo_search.py`), which drives a running server over HTTP. The
in-process variant documented in [README.md](README.md) imports the library
directly and needs a VectorGraphStore, so it still requires Neo4j.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) running locally with three models:

```sh
ollama pull nomic-embed-text   # embeddings
ollama pull llama3             # answer generation
ollama pull llama3.3           # LLM judge, see "Choosing a judge model"
```

`locomo10.json` is already in the repository under `evaluation/data/`, so
there is nothing to download.

Paths below assume:

```sh
REPO=~/work/ltm/MemMachine
RUN="uv run --project $REPO --frozen --all-extras"
WORK=~/locomo-run
mkdir -p $WORK
```

## Step 1: Start the server

```sh
cd $REPO
./dev-sqlite.sh start
```

This copies `sample_configs/episodic_memory_config.sqlite.sample` into a work
directory, downloads the NLTK stopwords the bm25 reranker needs, starts the
server and waits for it to report healthy. To do it by hand instead:

```sh
mkdir -p $WORK/server && cd $WORK/server
cp $REPO/sample_configs/episodic_memory_config.sqlite.sample configuration.yml
$RUN memmachine-nltk-setup                      # first run only
MEMORY_CONFIG=$PWD/configuration.yml HOST=127.0.0.1 PORT=8080 \
  $RUN memmachine-server
```

The port has to be 8080: `MemmachineHelperRestapiv2` defaults to
`http://localhost:8080` and the benchmark scripts do not expose a flag for it.

## Step 2: Ingest

```sh
cd $WORK          # metrics files are written to the working directory
$RUN python $REPO/evaluation/episodic_memory/restapiv2_locomo_ingest.py \
  --data-path $REPO/evaluation/data/locomo10.json \
  --conv-start 1 --conv-stop 1 --batch-size 10
```

`--conv-start` / `--conv-stop` select conversations; the dataset holds ten.
No model environment variables here - embedding happens server side, driven by
`configuration.yml`.

## Step 3: Search

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

The environment variables configure the model that writes the answers. Keep
`--conv-start` / `--conv-stop` the same as in step 2.

## Step 4: Judge

```sh
cd $REPO/evaluation/episodic_memory
OPENAI_API_KEY=ollama \
OPENAI_API_BASE=http://localhost:11434/v1 \
OPENAI_MODEL_NAME=llama3.3 \
$RUN python locomo_evaluate.py \
  --data-path $WORK/locomo_result.json \
  --target-path $WORK/evaluation_metrics.json
```

Two things to watch:

- Run this from `evaluation/episodic_memory/`. `locomo_evaluate.py` does
  `from llm_judge import evaluate_llm_judge`, so calling it by absolute path
  from elsewhere fails with `ModuleNotFoundError`.
- Its `--data-path` is the *result* file from step 3, not the dataset.

## Step 5: Score

`generate_scores.py` reads `evaluation_metrics.json` from the working
directory, which is why step 4 wrote that name:

```sh
cd $WORK
$RUN python $REPO/evaluation/episodic_memory/generate_scores.py
```

## Step 6: Clean up

```sh
cd $REPO
./dev-sqlite.sh stop     # or: reset, which also deletes the SQLite files
```

## A recorded run

One conversation (`--conv-start 1 --conv-stop 1`), 152 questions, on a 16-core
CPU-only machine with 38 GiB of RAM. Ollama served every model.

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

Categories are 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop. The
ordering is the expected one: single-hop highest, temporal lowest, multi-hop in
between.

| Step | Duration |
| --- | --- |
| Ingest | 15s |
| Search | 20m 53s |
| Judge | 28m 40s |
| Total | ~50m |

Storage was not the constraint. Ingest took fifteen seconds including 22,141
embedding tokens, and grew the two SQLite files from 260 KB to 8.2 MB. Search
answered each question in 8.2s on average and judging took 11.3s per question,
which is model inference in both cases. Judging is the slowest step because
`locomo_evaluate.py` iterates serially while search runs with `--max-workers`.

Search retrieved 5,000-7,000 memories per question without SQLite showing up in
the timings, but this was a single conversation. A ten-conversation run grows
the vector index tenfold and deserves its own measurement before assuming the
same holds.

## Choosing a judge model

Judging is harder than answering, and a model that is too small does not fail -
it agrees with everything, which produces a high score that means nothing.
Asked to grade "It raised awareness for ocean plastic pollution" against the
gold answer "mental health":

| Model | Correct answer | Wrong answer | "May 7th" vs "7 May 2023" |
| --- | --- | --- | --- |
| `llama3` | CORRECT | **CORRECT** | - |
| `llama3.3` | CORRECT | WRONG | CORRECT |
| `qwen3.5` | fails to parse | | |

`llama3` would have scored this run as near perfect regardless of what was
retrieved. `qwen3.5` raises `TypeError` inside `json_repair.loads()` before a
label is read. Use `llama3.3` or something comparable.

## What the numbers are not

These are not MemMachine performance figures. The run used one of ten
conversations, `llama3` for answers and `llama3.3` as judge rather than the
usual `gpt-4o-mini`, and `--top-k 20` instead of the default 50. Treat it as
evidence that the pipeline runs end to end on SQLite and produces sensible
numbers, and compare only against runs made under the same conditions.
