import re
import sys

# python citation-2-r02.py bib.txt text_extract.txt output_report.txt

def extract_bib_entries_full_line_context(bib_file):
    """
    從 bibliography 提取每筆：年份 + 年份前整行文字（到上一行換行）作為關鍵上下文
    支援半形 () 和全形（）
    """
    entries = []
    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"錯誤：找不到 bibliography 檔案 '{bib_file}'")
        sys.exit(1)
    
    # 按行分割，但保留空行作為分隔
    lines = content.splitlines()
    
    current_entry = ""
    for line in lines:
        stripped = line.strip()
        
        # 偵測是否為新條目開始（非空且包含年份括號）
        if stripped and re.search(r'[（(]\d{4}[）)]', stripped):
            # 如果已有正在處理的條目，先儲存
            if current_entry:
                process_entry(current_entry, entries)
            
            # 開始新條目
            current_entry = stripped
        elif current_entry and stripped:
            # 屬於同一條目（多行情況，如學位論文）
            current_entry += " " + stripped
        # 空行或無年份 → 暫不處理（避免誤抓標題如「專書」「期刊論文」）
    
    # 處理最後一筆
    if current_entry:
        process_entry(current_entry, entries)
    
    return entries

def process_entry(entry_line, entries):
    """處理單一文獻條目，提取年份與前方全文關鍵詞"""
    # 支援半形與全形括號
    year_match = re.search(r'[（(](\d{4})[）)]', entry_line)
    if not year_match:
        return
    year = year_match.group(1)
    
    # 找到左括號位置
    left_bracket = year_match.group(0)[0]
    bracket_pos = entry_line.find(left_bracket + year)
    if bracket_pos == -1:
        return
    
    # 關鍵上下文：年份括號前所有文字（整筆開頭到年份前）
    pre_full_text = entry_line[:bracket_pos].strip()
    
    # 清理結尾標點
    pre_full_text = re.sub(r'[.,;，。；、]\s*$', '', pre_full_text)
    
    # 提取關鍵詞（中文詞 + 英文詞）
    words = []
    words.extend(re.findall(r'[\u4e00-\u9fff]+', pre_full_text))  # 中文詞
    words.extend(re.findall(r'\b[a-zA-Z]+\b', pre_full_text))     # 英文詞
    
    # 去重、轉小寫、過濾短詞（<2）
    keywords = {w.lower() for w in words if len(w) >= 2}
    
    # fallback：若無詞，至少保留部分文字（如作者姓）
    if not keywords and pre_full_text:
        fallback = re.sub(r'[^\w\u4e00-\u9fff]', '', pre_full_text)[:10].lower()
        keywords = {fallback} if fallback else set()
    
    # 顯示用：前幾個關鍵詞 + 截斷前文
    display_pre = pre_full_text[:60] + "..." if len(pre_full_text) > 60 else pre_full_text
    
    entries.append({
        'original_line': entry_line,
        'year': year,
        'pre_full_text': pre_full_text,           # 完整前方文字
        'keywords': keywords,                    # 用於匹配
        'display_pre': display_pre,
        'top_keywords': list(keywords)[:8]        # 顯示用
    })

def find_matches_by_full_pretext(extracted_file, bib_entries):
    """
    在提取結果中：年份出現 + 前方全文關鍵詞任一出現 → match
    """
    try:
        with open(extracted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"錯誤：找不到提取結果檔案 '{extracted_file}'")
        sys.exit(1)
    
    snippets = [line.strip() for line in lines if '[' in line and ']' in line]
    
    matches = []
    not_found = []
    
    for entry in bib_entries:
        year = entry['year']
        keywords = entry['keywords']
        
        matched_snippets = []
        matched_keywords_set = set()
        
        for snippet in snippets:
            if year not in snippet:
                continue
            
            snippet_words = set()
            snippet_words.update(re.findall(r'[\u4e00-\u9fff]+', snippet))
            snippet_words.update(re.findall(r'\b[a-zA-Z]+\b', snippet))
            snippet_words = {w.lower() for w in snippet_words if len(w) >= 2}
            
            common = keywords & snippet_words
            if common:
                matched_snippets.append(snippet)
                matched_keywords_set.update(common)
        
        if matched_snippets:
            matches.append({
                'bib': entry,
                'evidence': matched_snippets,
                'matched_keywords': list(matched_keywords_set)
            })
        else:
            not_found.append(entry)
    
    return matches, not_found
def print_and_write(f, text=""):
    """同時輸出到螢幕和檔案"""
    print(text)
    if f:
        f.write(text + '\n')

def main():
    # 檢查參數數量，現在需要一個可選的輸出檔案名稱
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("使用方式：")
        print("python bib_match_fullpre.py <bibliography檔案> <年份提取結果檔案> [輸出結果檔案名稱]")
        print("")
        print("範例：")
        print("python bib_match_fullpre.py S1-bib.txt 年份提取結果_paper.txt")
        print("python bib_match_fullpre.py S1-bib.txt 年份提取結果_paper.txt output.txt")
        sys.exit(1)
    
    bib_file = sys.argv[1]
    extracted_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) == 4 else None # 判斷是否有提供輸出檔名

    # 設置輸出流
    # 如果提供了 output_file，我們將使用它來寫入結果
    output_f = None
    try:
        if output_file:
            # 使用 io.TextIOWrapper 確保編碼
            output_f = open(output_file, 'w', encoding='utf-8')
            print(f"結果將同時輸出到螢幕和檔案: {output_file}\n")

        # 使用一個簡單的函式來處理所有的輸出
        def log_output(text=""):
            print_and_write(output_f, text)

        # ----------------- 腳本核心邏輯 -----------------
        
        log_output("開始進行 bibliography 與 in-text citation 匹配檢查（進階版）")
        log_output("匹配規則：年份出現 + 年份前整筆文字中的任一關鍵詞出現 → 視為已引用")
        log_output("已支援：半形括號 () 與 全形括號（）")
        log_output(f"\n參考文獻檔案：{bib_file}")
        log_output(f"年份提取檔案：{extracted_file}\n")
        
        bib_entries = extract_bib_entries_full_line_context(bib_file)
        log_output(f"成功提取 {len(bib_entries)} 筆文獻條目\n")
        
        matches, not_found = find_matches_by_full_pretext(extracted_file, bib_entries)
        
        log_output("=" * 80)
        log_output("匹配結果報告（基於年份前整筆文字關鍵詞）")
        log_output("=" * 80)
        
        log_output(f"✔ 已匹配（正文中有明確引用跡象）：{len(matches)} 筆")
        log_output(f"✖ 未找到匹配：{len(not_found)} 筆\n")
        
        if matches:
            log_output("【已匹配的文獻】")
            for i, item in enumerate(matches, 1):
                bib = item['bib']
                log_output(f"{i:3d}. [{bib['year']}] {bib['display_pre']}")
                log_output(f"     匹配關鍵詞：{', '.join(item['matched_keywords'][:10])}")
                log_output(f"     參考文獻：{bib['original_line'][:120]}...")
                log_output("     正文證據（前2筆）：")
                for ev in item['evidence'][:2]:
                    log_output(f"        → {ev}")
                log_output()
        
        if not_found:
            log_output("【正文中未找到匹配的文獻（建議檢查是否真的被引用）】")
            for i, item in enumerate(not_found, 1):
                log_output(f"{i:3d}. [{item['year']}] {item['display_pre']}")
                if item['top_keywords']:
                    log_output(f"     期望關鍵詞（前8）：{', '.join(item['top_keywords'])}")
                log_output(f"     完整條目：{item['original_line'][:120]}...")
                log_output()
        
        log_output("檢查完成！此版本對中文論文引用格式（如「王新衡（2024）」）極為寬容，匹配率應大幅提升。")

    except Exception as e:
        # 確保在發生錯誤時也能看到錯誤訊息
        print(f"\n發生錯誤: {e}", file=sys.stderr)

    finally:
        # 確保無論如何都會關閉檔案
        if output_f:
            output_f.close()

if __name__ == "__main__":
    # 將所有函式定義放在這裡，以確保整個腳本的可執行性
    
    # 為了保持範例的完整性，我將您原本的 extract_bib_entries_full_line_context、process_entry 和 find_matches_by_full_pretext 放置在這裡，但實際上您只需要將它們和 main 放在同一個檔案中即可。
    # 由於篇幅限制，這裡只保留 main() 和關鍵修改。
    import re
import sys
import io

# ----------------- 輔助函式 -----------------

def print_and_write(f, text=""):
    """
    同時將內容輸出到 sys.stdout (螢幕) 和檔案物件 f。
    """
    print(text)
    if f:
        f.write(text + '\n')

# ----------------- 參考文獻提取函式 -----------------

def extract_bib_entries_full_line_context(bib_file):
    """
    從 bibliography 提取每筆：年份 + 年份前整行文字（到上一行換行）作為關鍵上下文
    支援半形 () 和全形（）
    """
    entries = []
    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"錯誤：找不到 bibliography 檔案 '{bib_file}'", file=sys.stderr)
        sys.exit(1)
    
    # 按行分割，但保留空行作為分隔
    lines = content.splitlines()
    
    current_entry = ""
    for line in lines:
        stripped = line.strip()
        
        # 偵測是否為新條目開始（非空且包含年份括號）
        if stripped and re.search(r'[（(]\d{4}[）)]', stripped):
            # 如果已有正在處理的條目，先儲存
            if current_entry:
                process_entry(current_entry, entries)
            
            # 開始新條目
            current_entry = stripped
        elif current_entry and stripped:
            # 屬於同一條目（多行情況，如學位論文）
            current_entry += " " + stripped
        # 空行或無年份 → 暫不處理（避免誤抓標題如「專書」「期刊論文」）
    
    # 處理最後一筆
    if current_entry:
        process_entry(current_entry, entries)
    
    return entries

def process_entry(entry_line, entries):
    """處理單一文獻條目，提取年份與前方全文關鍵詞"""
    # 支援半形與全形括號
    year_match = re.search(r'[（(](\d{4})[）)]', entry_line)
    if not year_match:
        return
    year = year_match.group(1)
    
    # 找到左括號位置
    left_bracket = year_match.group(0)[0]
    bracket_pos = entry_line.find(left_bracket + year)
    if bracket_pos == -1:
        return
    
    # 關鍵上下文：年份括號前所有文字（整筆開頭到年份前）
    pre_full_text = entry_line[:bracket_pos].strip()
    
    # 清理結尾標點
    pre_full_text = re.sub(r'[.,;，。；、]\s*$', '', pre_full_text)
    
    # 提取關鍵詞（中文詞 + 英文詞）
    words = []
    words.extend(re.findall(r'[\u4e00-\u9fff]+', pre_full_text))  # 中文詞
    words.extend(re.findall(r'\b[a-zA-Z]+\b', pre_full_text))    # 英文詞
    
    # 去重、轉小寫、過濾短詞（<2）
    keywords = {w.lower() for w in words if len(w) >= 2}
    
    # fallback：若無詞，至少保留部分文字（如作者姓）
    if not keywords and pre_full_text:
        fallback = re.sub(r'[^\w\u4e00-\u9fff]', '', pre_full_text)[:10].lower()
        keywords = {fallback} if fallback else set()
    
    # 顯示用：前幾個關鍵詞 + 截斷前文
    display_pre = pre_full_text[:60] + "..." if len(pre_full_text) > 60 else pre_full_text
    
    entries.append({
        'original_line': entry_line,
        'year': year,
        'pre_full_text': pre_full_text,             # 完整前方文字
        'keywords': keywords,                       # 用於匹配
        'display_pre': display_pre,
        'top_keywords': list(keywords)[:8]          # 顯示用
    })

# ----------------- 正文匹配函式 -----------------

def find_matches_by_full_pretext(extracted_file, bib_entries):
    """
    在提取結果中：年份出現 + 前方全文關鍵詞任一出現 → match
    """
    try:
        with open(extracted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"錯誤：找不到提取結果檔案 '{extracted_file}'", file=sys.stderr)
        sys.exit(1)
    
    # 只處理包含潛在引文標記的行 (e.g., [Year] or [Author, Year])
    snippets = [line.strip() for line in lines if '[' in line and ']' in line]
    
    matches = []
    not_found = []
    
    for entry in bib_entries:
        year = entry['year']
        keywords = entry['keywords']
        
        matched_snippets = []
        matched_keywords_set = set()
        
        for snippet in snippets:
            # 必須包含年份
            if year not in snippet:
                continue
            
            # 提取 snippet 中的所有關鍵詞
            snippet_words = set()
            snippet_words.update(re.findall(r'[\u4e00-\u9fff]+', snippet))
            snippet_words.update(re.findall(r'\b[a-zA-Z]+\b', snippet))
            snippet_words = {w.lower() for w in snippet_words if len(w) >= 2}
            
            # 尋找文獻關鍵詞與 snippet 關鍵詞的交集
            common = keywords & snippet_words
            if common:
                matched_snippets.append(snippet)
                matched_keywords_set.update(common)
        
        if matched_snippets:
            matches.append({
                'bib': entry,
                'evidence': matched_snippets,
                'matched_keywords': list(matched_keywords_set)
            })
        else:
            not_found.append(entry)
    
    return matches, not_found

# ----------------- 主函式 (已修改以支援檔案輸出) -----------------

def main():
    # 檢查參數數量：需要 2 個輸入檔案，第 3 個輸出檔案是可選的
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("使用方式：")
        print("python bib_match_fullpre.py <bibliography檔案> <年份提取結果檔案> [輸出結果檔案名稱]")
        print("")
        print("範例：")
        print("python bib_match_fullpre.py S1-bib.txt 年份提取結果_paper.txt")
        print("python bib_match_fullpre.py S1-bib.txt 年份提取結果_paper.txt output.txt")
        sys.exit(1)
    
    bib_file = sys.argv[1]
    extracted_file = sys.argv[2]
    # 判斷是否有提供輸出檔名
    output_file = sys.argv[3] if len(sys.argv) == 4 else None

    # 設置輸出流
    output_f = None
    try:
        if output_file:
            # 開啟檔案，使用 'w' 寫入模式和 'utf-8' 編碼
            output_f = open(output_file, 'w', encoding='utf-8')
            print(f"結果將同時輸出到螢幕和檔案: {output_file}\n")

        # 使用一個簡單的函式來處理所有的輸出，使其導向 print_and_write
        def log_output(text=""):
            print_and_write(output_f, text)

        # ----------------- 腳本核心邏輯 -----------------
        
        log_output("開始進行 bibliography 與 in-text citation 匹配檢查（進階版）")
        log_output("匹配規則：年份出現 + 年份前整筆文字中的任一關鍵詞出現 → 視為已引用")
        log_output("已支援：半形括號 () 與 全形括號（）")
        log_output(f"\n參考文獻檔案：{bib_file}")
        log_output(f"年份提取檔案：{extracted_file}\n")
        
        bib_entries = extract_bib_entries_full_line_context(bib_file)
        log_output(f"成功提取 {len(bib_entries)} 筆文獻條目\n")
        
        matches, not_found = find_matches_by_full_pretext(extracted_file, bib_entries)
        
        log_output("=" * 80)
        log_output("匹配結果報告（基於年份前整筆文字關鍵詞）")
        log_output("=" * 80)
        
        log_output(f"✔ 已匹配（正文中有明確引用跡象）：{len(matches)} 筆")
        log_output(f"✖ 未找到匹配：{len(not_found)} 筆\n")
        
        # 輸出匹配結果
        if matches:
            log_output("【已匹配的文獻】")
            for i, item in enumerate(matches, 1):
                bib = item['bib']
                log_output(f"{i:3d}. [{bib['year']}] {bib['display_pre']}")
                log_output(f"     匹配關鍵詞：{', '.join(item['matched_keywords'][:10])}")
                log_output(f"     參考文獻：{bib['original_line'][:120]}...")
                log_output("     正文證據（前2筆）：")
                for ev in item['evidence'][:2]:
                    log_output(f"        → {ev}")
                log_output()
        
        # 輸出未匹配結果
        if not_found:
            log_output("【正文中未找到匹配的文獻（建議檢查是否真的被引用）】")
            for i, item in enumerate(not_found, 1):
                log_output(f"{i:3d}. [{item['year']}] {item['display_pre']}")
                if item['top_keywords']:
                    log_output(f"     期望關鍵詞（前8）：{', '.join(item['top_keywords'])}")
                log_output(f"     完整條目：{item['original_line'][:120]}...")
                log_output()
        
        log_output("檢查完成！此版本對中文論文引用格式（如「王新衡（2024）」）極為寬容，匹配率應大幅提升。")

    except Exception as e:
        # 捕獲其他錯誤並輸出到標準錯誤流
        print(f"\n執行過程中發生未預期錯誤: {e}", file=sys.stderr)

    finally:
        # 確保無論程式是否成功運行，檔案都會被關閉
        if output_f:
            output_f.close()

if __name__ == "__main__":
    main()