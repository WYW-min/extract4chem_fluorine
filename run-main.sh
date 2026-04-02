pixi run main-signal-before --inpath data/out/聚酰亚胺/20260319165741/doc_split/raw_20260319165541.jsonl && 
pixi run main-signal-predict --inpath data/out/聚酰亚胺/20260319165741/main_signal_before/raw_20260319165541.jsonl -b 100 &&
pixi run main-signal-after --before-jsonl data/out/聚酰亚胺/20260319165741/main_signal_before/raw_20260319165541.jsonl \
    -t data/out/聚酰亚胺/20260319165741/main_signal_predict/temp 
