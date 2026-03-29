"""AI评论分类模块。"""

import csv
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Callable

SYSTEM_PROMPT = """You are a comment classifier and reply generator. For each comment:
1. Classify it into one category: positive(正面), negative(负面), question(问题), suggestion(建议), spam(垃圾信息), other(其他)
2. Provide confidence score (0-100)
3. Decide action: reply(回复), ignore(忽略), flag_review(待审)
4. Explain the reason briefly
5. Generate a suitable reply content if action is "reply"

Return JSON array format:
[{
  "category": "positive",
  "confidence": 95,
  "action": "reply",
  "reason": "用户表达了喜爱和认可",
  "generated_reply": "感谢您的认可，我们会继续努力！"
}]"""


def extract_json(text: str) -> str:
    """从文本中提取JSON数组。"""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    matches = re.findall(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if matches:
        return matches[-1]
    return text


def load_config() -> tuple:
    """加载MiniMax API配置。"""
    api_key = os.getenv("MINIMAX_API_KEY", "")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
    return api_key, base_url


def classify_single_batch(client, batch: list) -> list:
    """对单批评论进行分类。"""
    comment_text = "\n".join(
        [
            f"[{c['comment_id']}] {c['text'].encode()[:500].decode('utf-8', errors='ignore')}"
            for c in batch
        ]
    )

    try:
        response = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Classify these comments:\n\n{comment_text}",
                },
            ],
            temperature=1.0,
            max_tokens=4096,
        )
        raw = response.choices[0].message.content
        text = extract_json(raw)
        batch_results = json.loads(text)

        if isinstance(batch_results, list):
            for i, result in enumerate(batch_results):
                result["id"] = batch[i]["comment_id"]
            return batch_results
        else:
            batch_results["id"] = batch[0]["comment_id"]
            return [batch_results]
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        return [
            {
                "id": c["comment_id"],
                "category": "error",
                "confidence": 0,
                "action": "flag_review",
                "reason": f"Classification error: {str(e)[:100]}",
                "generated_reply": "",
            }
            for c in batch
        ]


def execute_classify_task(
    task_id: str,
    file_path: str,
    batch_size: int = 20,
    workers: int = 5,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> dict:
    """执行分类任务。"""
    from openai import OpenAI

    api_key, base_url = load_config()
    if not api_key:
        return {"status": "failed", "error": "MINIMAX_API_KEY not configured"}

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        comments = []
        original_rows = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if row.get("评论内容"):
                    original_rows.append(row)
                    comments.append(
                        {"comment_id": f"c{i}", "text": row["评论内容"][:500]}
                    )

        total_batches = (len(comments) + batch_size - 1) // batch_size

        batches = [
            (i, comments[i : i + batch_size])
            for i in range(0, len(comments), batch_size)
        ]
        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(classify_single_batch, client, batch): batch
                for batch in batches
            }
            for future in as_completed(futures):
                batch_results = future.result()
                results.extend(batch_results)
                completed += 1
                progress = int((completed / total_batches) * 100)
                if progress_callback:
                    progress_callback(progress)

        class_map = {c["id"]: c for c in results}
        classified = []
        for i, comment in enumerate(comments):
            cid = comment["comment_id"]
            cls = class_map.get(
                cid,
                {
                    "category": "unclassified",
                    "confidence": 0,
                    "action": "flag_review",
                    "reason": "Not classified",
                    "generated_reply": "",
                },
            )
            classified.append(
                {
                    **comment,
                    "classification": cls.get("category", "unclassified"),
                    "confidence": cls.get("confidence", 0),
                    "action": cls.get("action", "flag_review"),
                    "reason": cls.get("reason", ""),
                    "generated_reply": cls.get("generated_reply", ""),
                }
            )

        output_filename = file_path.replace(".csv", "_classified.csv")
        fieldnames = list(original_rows[0].keys()) + [
            "classification",
            "confidence",
            "action",
            "reason",
            "generated_reply",
        ]
        with open(output_filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i, c in enumerate(classified):
                row = dict(original_rows[i])
                row["classification"] = c.get("classification", "")
                row["confidence"] = c.get("confidence", "")
                row["action"] = c.get("action", "")
                row["reason"] = c.get("reason", "")
                row["generated_reply"] = c.get("generated_reply", "")
                writer.writerow(row)

        counts = {}
        for c in classified:
            cat = c.get("classification", "unknown")
            counts[cat] = counts.get(cat, 0) + 1

        return {
            "status": "completed",
            "file_path": output_filename,
            "summary": counts,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}
