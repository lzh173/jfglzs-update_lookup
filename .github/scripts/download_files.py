#!/usr/bin/env python3
import requests
import os
import json
import hashlib
from datetime import datetime

def load_config():
    """加载URL配置"""
    config_file = '.github/scripts/urls_config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"urls": []}

def get_url_info(url_id):
    """根据URL ID获取URL信息"""
    config = load_config()
    for url_config in config['urls']:
        if url_config['id'] == url_id:
            return url_config
    return None

def download_file(url_config, filename):
    """下载文件到指定路径"""
    try:
        url = url_config['url']
        timeout = url_config.get('timeout', 30)
        
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # 创建downloads目录
        os.makedirs('downloads', exist_ok=True)
        filepath = os.path.join('downloads', filename)
        
        # 写入文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(filepath)
        file_hash = hashlib.md5(response.content).hexdigest()
        
        return {
            'success': True,
            'filepath': filepath,
            'filename': filename,
            'size': file_size,
            'hash': file_hash,
            'url': url,
            'url_name': url_config.get('name', url_config['id']),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename,
            'url': url_config['url'],
            'url_name': url_config.get('name', url_config['id'])
        }

def generate_filename(url_config):
    """生成下载文件名"""
    url_id = url_config['id']
    url_name = url_config.get('name', url_id)
    original_url = url_config['url']
    
    # 从URL提取文件名
    base_filename = os.path.basename(original_url) or f"{url_id}.bin"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    name, ext = os.path.splitext(base_filename)
    if not ext:
        ext = '.bin'
    
    # 清理文件名中的特殊字符
    safe_name = re.sub(r'[^\w\-_.]', '_', name)
    filename = f"{safe_name}_{timestamp}{ext}"
    
    return filename

def main():
    # 获取发生变化的URL
    changed_urls_str = os.environ.get('CHANGED_URLS', '')
    changed_urls = [url.strip() for url in changed_urls_str.split(',') if url.strip()]
    
    if not changed_urls:
        print("没有检测到变化的URL，跳过下载")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write('downloaded_files_list=没有文件需要下载\n')
            fh.write('total_downloaded=0\n')
        return
    
    print(f"需要下载的URL: {changed_urls}")
    
    # 下载文件
    download_results = []
    downloaded_files = []
    
    for url_id in changed_urls:
        url_config = get_url_info(url_id)
        if not url_config:
            print(f"警告: 未找到URL配置: {url_id}")
            continue
            
        filename = generate_filename(url_config)
        url_name = url_config.get('name', url_id)
        
        print(f"下载 {url_name} ({url_id}): {url_config['url']} -> {filename}")
        
        result = download_file(url_config, filename)
        download_results.append(result)
        
        if result['success']:
            downloaded_files.append(result)
            print(f"  下载成功: {filename} ({result['size']} 字节)")
        else:
            print(f"  下载失败: {result['error']}")
    
    # 生成下载文件列表
    file_list = []
    for file_info in downloaded_files:
        size_kb = file_info['size'] / 1024
        file_list.append(f"- {file_info['filename']} ({size_kb:.1f} KB) - {file_info['url_name']}")
    
    # 设置GitHub Actions输出
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        if file_list:
            files_output = "\n".join(file_list)
            fh.write(f'downloaded_files_list={files_output}\n')
        else:
            fh.write('downloaded_files_list=没有文件被下载\n')
        
        fh.write(f'total_downloaded={len(downloaded_files)}\n')
    
    # 保存下载记录
    os.makedirs('.github/scripts', exist_ok=True)
    with open('.github/scripts/download_history.json', 'a') as f:
        record = {
            'timestamp': datetime.now().isoformat(),
            'run_id': os.environ.get('GITHUB_RUN_ID', 'unknown'),
            'downloads': download_results
        }
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"下载完成: {len(downloaded_files)} 个文件")

if __name__ == "__main__":
    main()