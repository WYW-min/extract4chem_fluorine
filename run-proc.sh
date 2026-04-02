pixi run proc-before -i data/out/聚酰亚胺/20260319165741/main_signal_after/raw_20260319165541.jsonl \
        -d data/out/聚酰亚胺/20260319165741/doc_split/raw_20260319165541.jsonl  &&

pixi run proc-predict -i data/out/聚酰亚胺/20260319165741/process_before/raw_20260319165541.jsonl -b 50 &&

pixi run proc-after -i data/out/聚酰亚胺/20260319165741/process_before/raw_20260319165541.jsonl \
    -t data/out/聚酰亚胺/20260319165741/process_predict/temp