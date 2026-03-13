import asyncio
from itertools import batched
from typing import Set, Tuple
from pydantic import BaseModel
from extract4chem_fluorine.tools import processDoc, extract_doi
from pathlib import Path
import os
import orjsonl
from extract4chem_fluorine.llm_config import llm_manager
from langchain_core.prompts import ChatPromptTemplate
from extract4chem_fluorine.entities.synthesis import SynthesisResult
from extract4chem_fluorine.tools import MyJSONParser
import orjson
from xopen import xopen
from tqdm import tqdm
from extract4chem_fluorine.tools.data_tool import (
    add_nowstr,
    count_jsonlines,
    get_section,
)


def run_chain(chain, input_data):

    results = list(chain.stream(input_data))
    if not results:
        return None
    else:
        return results[-1]


async def arun_chain(chain, input_data):

    results = [item async for item in chain.astream(input_data)]
    if not results:
        return None
    elif isinstance(results[-1], Exception):
        return {"error": str(results[-1])}
    else:
        return results[-1]


def get_final_data(
    record: dict, chain_response: BaseModel | Exception, other_info: None | dict = None
) -> dict:
    if isinstance(chain_response, Exception):
        chain_response = {"error": str(chain_response)}

    final_data = (other_info or {}) | record | {"syn_extract_result": chain_response}

    if isinstance(final_data["syn_extract_result"], BaseModel):
        final_data["syn_extract_result"] = final_data["syn_extract_result"].model_dump(
            mode="json"
        )
    return final_data


def yield_input(inpath, already_ids: Set[Tuple[str, str]] | None = None):
    if not already_ids:
        already_ids = set()

    raw_text_path = Path("/Data_two/wyw/data/AI4CHEM/分子筛/md_3592")
    for record in orjsonl.stream(inpath):
        # 读取对应的文本
        raw_text = (raw_text_path / record["file_name"]).read_text(encoding="utf-8")
        splited_texts = processDoc(raw_text)
        input_data = get_section(splited_texts)
        need_cols = ["id", "aliases"]

        for material_info in record["main_extract_result"]["parse"]["material_ids"]:
            cur_id = (record["file_name"], material_info["id"])
            if cur_id in already_ids:
                continue
            yield {
                "id": {
                    "file_name": cur_id[0],
                    "material_id": cur_id[1],
                },
                "chain_input": {
                    "paper_info": input_data["effective_section"],
                    "material_info": {
                        k: v for k, v in material_info.items() if k in need_cols
                    },
                },
            }


def get_chain(prompt_path: Path, data_model: BaseModel, llm_name="qwen"):
    main_llm = llm_manager[llm_name]
    prompt_temp = ChatPromptTemplate.from_template(
        Path(prompt_path).read_text(encoding="utf-8")
    )
    syn_parser = MyJSONParser(data_model)
    main_chain = (
        prompt_temp.partial(schema_define=syn_parser.get_format_instructions())
        | main_llm
        | syn_parser
    )
    return main_chain


from datetime import datetime

now_str = datetime.now().strftime("%Y%m%d%H%M%S")


def enhance_config(raw_config):
    config = raw_config.copy()

    if config.get("CHECKPOINT_PATH") is None:
        return config

    str_array = Path(config["CHECKPOINT_PATH"]).stem.split("_", maxsplit=1)
    if len(str_array) >= 2:
        checkpoint_suffix = Path(config["CHECKPOINT_PATH"]).stem.split("_", maxsplit=1)[
            1
        ]
        config["OUTPATH"] = (
            config["OUTPATH"] + f"/{config["name"]}_{checkpoint_suffix}_{now_str}.jsonl"
        )
    else:
        config["OUTPATH"] = config["OUTPATH"] + f"/{config["name"]}_{now_str}.jsonl"
    config["already_ids"] = set()
    # 获取重复集合
    result_key = None

    for record in orjsonl.stream(config["CHECKPOINT_PATH"]):
        if result_key == None:
            for k in record:
                if "result" in k:
                    result_key = k
                    break
            else:
                raise Exception('不能找到结果对应的键，应包含"result"子串')
        elif record.get(result_key, {}).get("error") is None:
            config["already_ids"].add((record["file_name"], record["material_id"]))
    print(f"跳过条数：{len(config["already_ids"])}")
    return config


SYN_CONFIG = {
    "name": "syn",
    "LLM": "gpt_low",
    "INPATH": "data/out/分子筛/20260108160000/main.jsonl",
    "OUTPATH": f"./data/out/分子筛",
    "PROMPT_PATH": "./prompts/synthesis.txt",
    "READ_NUM": 300,
    "SCHEMA_DEFINE": SynthesisResult,
    "CHECKPOINT_PATH": "./data/out/分子筛/20260108160000/syn.jsonl",
}


async def main(config):
    config = enhance_config(config)
    main_chain = get_chain(
        Path(config["PROMPT_PATH"]), config["SCHEMA_DEFINE"], config["LLM"]
    )
    inpath, outpath = Path(config["INPATH"]), add_nowstr(Path(config["OUTPATH"]))
    pbars = tqdm(desc="抽取进度", total=count_jsonlines(inpath))
    with xopen(outpath, "wb") as fout:
        for records in batched(
            yield_input(inpath, already_ids=config.get("already_ids")),
            n=config["READ_NUM"],
        ):
            ga_coroutine = [arun_chain(main_chain, r["chain_input"]) for r in records]
            ga_coroutine_results = await asyncio.gather(
                *ga_coroutine, return_exceptions=True
            )
            final_data = [
                get_final_data(r["id"], run_chain_result)
                for r, run_chain_result in zip(records, ga_coroutine_results)
            ]
            fout.write(b"".join(orjson.dumps(d) + b"\n" for d in final_data))
            pbars.update(len(records))


if __name__ == "__main__":
    asyncio.run(main(SYN_CONFIG))
