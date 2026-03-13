import asyncio
from itertools import batched
from pydantic import BaseModel
from extract4chem_fluorine.tools import processDoc,extract_doi
from pathlib import Path
import os
import orjsonl
from extract4chem_fluorine.llm_config import llm_manager
from langchain_core.prompts import ChatPromptTemplate
from extract4chem_fluorine.entities.material_ID import Er4MaterialId
from extract4chem_fluorine.tools import MyJSONParser
import orjson
from xopen import xopen
from tqdm import tqdm
from extract4chem_fluorine.tools.global_state_manager import gs_manager
from extract4chem_fluorine.tools.data_tool import add_nowstr
def get_chain_input(splited_texts):
    main_input = {
    "title": f"# {splited_texts[0]["content_title"]}",
    "abstract": splited_texts[0]["content"],
    "experiment": ""
    }
    abstract_info = []
    exp_infos = []
    index = 0

    while (index<=len(splited_texts)-1) and ("INTRODUCT" not in splited_texts[index]["content_title"].upper()):
        abstract_info.append(f"# {splited_texts[index]["content_title"]}\n{splited_texts[index]["content"]}")
        index += 1
        
    while index<=len(splited_texts)-1:
        if "EXPERIM" in splited_texts[index]["content_title"].upper():
            raw_exp_title = splited_texts[index]["content_title"]
            exp_infos.append(f"# {splited_texts[index]["content_title"]}\n{splited_texts[index]["content"]}")
            break
        index += 1



    for block in splited_texts[index+1:]:
        if not os.path.commonprefix([block["content_title"].strip(), raw_exp_title.strip()]):
            break
        exp_infos.append(f"# {block["content_title"]}\n{block["content"]}")
    main_input["experiment"] = "\n\n".join(exp_infos)
    main_input["abstract"] = "\n\n".join(abstract_info)
    return main_input

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
        return {
            "error": str(results[-1])
        }
    else:
        return results[-1]
unknown_flag = 0 
def get_final_data(record, chain_response, other_info = None | dict):
    
    final_data = (other_info or {}) | {
        "file_name": record.get("file_name", None),
        "main_extract_result" : chain_response
    } 
    
    
    global unknown_flag
    if final_data["file_name"] is None:
        final_data["file_name"] = f"unknown_{unknown_flag}"
        unknown_flag += 1
    
    if isinstance(final_data["main_extract_result"], BaseModel):
        final_data["main_extract_result"] = final_data["main_extract_result"].model_dump(mode="json")
    return final_data
    

INPATH = "data/out/分子筛/raw_20260108.jsonl"
OUTPATH = "./data/out/分子筛/main.jsonl"
PROMPT_PATH = "./prompts/主信号抽取.txt"
READ_NUM = 200

async def main():
    main_llm = llm_manager["gpt_low"]
    prompt_temp = ChatPromptTemplate.from_template(Path(PROMPT_PATH).read_text(encoding="utf-8"))

    main_chain = prompt_temp | main_llm  | MyJSONParser(Er4MaterialId)
    
    outpath = add_nowstr(Path(OUTPATH))

    
    
    inpaths = sorted(list(orjsonl.stream(INPATH)), key=lambda x: x.get("file_name", ""))
    
    pbars = tqdm(desc = "抽取进度", total = len(inpaths))
    with xopen(outpath, "wb") as fout:
        for records in batched(inpaths, n =READ_NUM):
            
            splited_texts = [processDoc(record["content"]) for record in records]
            input_data = [ get_chain_input(s) for s in  splited_texts]
            ga_coroutine = [arun_chain(main_chain, input) for input in input_data]
            ga_coroutine_results = await asyncio.gather(*ga_coroutine, return_exceptions=True)
            for record, run_chain_result in zip(records, ga_coroutine_results):
                if isinstance(run_chain_result, Exception):
                    run_chain_result = {"error": str(run_chain_result)}
                
                final_data = get_final_data(record, run_chain_result, {"doi": extract_doi(record["content"])})
                fout.write(orjson.dumps(final_data) + b"\n")
            pbars.update(len(records))
            
if __name__ == "__main__":
    asyncio.run(main())