#!/usr/bin/env python3
import requests
import hashlib
import os
import json
from datetime import datetime
import sys

def save_change_details(changed_urls):
    """保存变化详情供下载脚本使用"""
    change_file = '.github/scripts/changed_urls.json'
    os.makedirs(os.path.dirname(change_file), exist_ok=True)
    
    with open(change_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'changed_urls': changed_urls,
            'run_id': os.environ.get('GITHUB_RUN_ID', 'unknown')
        }, f, indent=2)


def get_content_hash(url):
    """获取URL内容的哈希值"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content
        return hashlib.md5(content).hexdigest(), len(content), True
    except Exception as e:
        return f"error: {str(e)}", 0, False

def load_previous_hashes():
    """加载之前存储的哈希值"""
    hash_file = '.github/scripts/url_hashes.json'
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            return json.load(f)
    return {}

def save_current_hashes(hashes):
    """保存当前哈希值"""
    os.makedirs('.github/scripts', exist_ok=True)
    hash_file = '.github/scripts/url_hashes.json'
    with open(hash_file, 'w') as f:
        json.dump(hashes, f, indent=2)

def main():
    # 从环境变量获取URL
    urls = {
        'url1': os.environ.get('URL_1'),
        'url2': os.environ.get('URL_2'),
        'url3': os.environ.get('URL_3')
    }
    
    # 移除空的URL
    urls = {k: v for k, v in urls.items() if v}
    
    if not urls:
        print("错误：没有配置有效的URL")
        sys.exit(1)
    
    # 加载之前的哈希值
    previous_hashes = load_previous_hashes()
    current_hashes = {}
    changes = []
    status_messages = []
    
    has_changes = False
    
    changed_urls = []
    has_changes = False
    
    for url_id, url in urls.items():
        print(f"检查 {url_id}: {url}")
        
        current_hash, size, success = get_content_hash(url)
        current_hashes[url_id] = {
            'hash': current_hash,
            'size': size,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'success': success
        }
        
        if not success:
            status_msg = f"获取失败: {current_hash}"
            changes.append(f"❌ {url_id} 获取失败")
        elif url_id not in previous_hashes:
            status_msg = "首次检查"
            changes.append(f"✅ {url_id} 首次检查")
            changed_urls.append(url_id)
            has_changes = True
        elif previous_hashes[url_id].get('hash') != current_hash:
            old_size = previous_hashes[url_id].get('size', 0)
            status_msg = f"内容变化: {old_size} → {size} 字节"
            changes.append(f"🔄 {url_id} 内容已变化 ({old_size} → {size} 字节)")
            changed_urls.append(url_id)
            has_changes = True
        else:
            status_msg = "无变化"
            changes.append(f"⚪ {url_id} 无变化")
        
        status_messages.append(f"{url_id}: {status_msg}")
        print(f"  {status_msg}")
    
    # 保存当前哈希值
    save_current_hashes(current_hashes)
    
    # 保存变化详情
    if has_changes:
        save_change_details(changed_urls)
    
    # 设置GitHub Actions输出
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        fh.write(f'changed={str(has_changes).lower()}\n')
        fh.write(f'change_details={chr(10).join(changes)}\n')
        fh.write(f'url1_status={status_messages[0] if len(status_messages) > 0 else "N/A"}\n')
        fh.write(f'url2_status={status_messages[1] if len(status_messages) > 1 else "N/A"}\n')
        fh.write(f'url3_status={status_messages[2] if len(status_messages) > 2 else "N/A"}\n')
        fh.write(f'changed_urls={",".join(changed_urls)}\n')
    
    if has_changes:
        print(f"检测到内容变化，将下载文件: {changed_urls}")
    else:
        print("未检测到内容变化")
        

if __name__ == "__main__":
    main()