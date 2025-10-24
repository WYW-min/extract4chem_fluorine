
from langchain_text_splitters import MarkdownHeaderTextSplitter
from bidict import bidict
def processDoc(markdown_document):
    """
    处理文档段落列表 (md_splits)，提取相关内容，清理标题，替换 Markdown 媒体，
    并过滤掉不相关的段落。

    Args:
        markdown_document (str): Markdown 文档内容。

    Returns:
        list: 包含已处理和过滤的文档段落信息的列表。
              每个元素包含 'title_level'、'content_title' 和 'content' 键。
    """
    headers_to_split_on = [
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3"),
        ("####", "H4")
    ]
    # 创建 Markdown 分割器实例
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on, 
        strip_headers=False
    )
    levels = [x[1] for x in headers_to_split_on]
    # 分割 Markdown 文档
    md_splits = splitter.split_text(markdown_document)
    bimap_level = bidict(headers_to_split_on)
    processed_splits = []
    # 遍历分割后的文档段落并处理
    for record in md_splits:
        if not record.metadata:
            continue

        split_info = {}
        cur_level = None
        cur_title = None

        # 查找有效的标题级别和标题文本
        for k, v in record.metadata.items():
            if k in levels:
                cur_level, cur_title = k, v
                split_info["title_level"] = k
                split_info["content_title"] = cur_title.strip()
                break
        
        # 如果没有找到有效级别则跳过
        if cur_level is None:
            continue

        # 构造标题字符串并从内容中移除
        title_str = " ".join([
            bimap_level.inverse.get(cur_level, ""),
            cur_title
        ])
        split_info["content"] = record.page_content.strip().lstrip(title_str).strip()
        processed_splits.append(split_info)
    return processed_splits
    
