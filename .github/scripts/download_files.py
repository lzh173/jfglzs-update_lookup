#!/usr/bin/env python3
import requests
import os
import json
import hashlib
from datetime import datetime
import glob

def download_file(url, filename):
    """下载文件到指定路径"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 创建downloads目录
        os.makedirs('downloads', exist_ok=True)
        
        filepath = os.path.join('downloads', filename)
        
        # 写入文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # 获取文件信息
        file_size = os.path.getsize(filepath)
        file_hash = hashlib.md5(response.content).hexdigest()
        
        return {
            'success': True,
            'filepath': filepath,
            'filename': filename,
            'size': file_size,
            'hash': file_hash,
            'url': url,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename,
            'url': url
        }

def get_url_mapping():
    """获取URL到文件名的映射"""
    # 从环境变量获取URL
    urls = {
        'url1': os.environ.get('URL_1'),
        'url2': os.environ.get('URL_2'),
        'url3': os.environ.get('URL_3')
    }
    
    # 生成文件名映射
    mapping = {}
    for url_id, url in urls.items():
        if url:
            # 从URL提取文件名，如果没有则使用URL ID
            filename = os.path.basename(url) or f"{url_id}.bin"
            # 添加时间戳避免重名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            if not ext:  # 如果没有扩展名，尝试从Content-Type推断
                ext = '.bin'
            filename = f"{name}_{timestamp}{ext}"
            mapping[url_id] = {'url': url, 'filename': filename}
    
    return mapping

def load_changed_urls():
    """加载发生变化的URL信息"""
    try:
        # 从monitor步骤的输出文件读取变化信息
        with open(os.environ.get('GITHUB_OUTPUT', ''), 'r') as f:
            lines = f.readlines()
        
        changed_urls = []
        for line in lines:
            if line.startswith('change_details='):
                # 解析变化详情
                details = line.split('=', 1)[1].strip()
                if '变化' in details or '首次检查' in details:
                    # 提取URL ID
                    for url_id in ['url1', 'url2', 'url3']:
                        if url_id in details:
                            changed_urls.append(url_id)
                break
        return changed_urls
    except:
        # 如果无法读取，默认下载所有URL
        return ['url1', 'url2', 'url3']

def main():
    # 获取URL映射
    url_mapping = get_url_mapping()
    
    # 获取发生变化的URL
    changed_urls = load_changed_urls()
    
    print(f"需要下载的URL: {changed_urls}")
    
    # 下载文件
    download_results = []
    downloaded_files = []
    
    for url_id in changed_urls:
        if url_id in url_mapping:
            url_info = url_mapping[url_id]
            print(f"下载 {url_id}: {url_info['url']} -> {url_info['filename']}")
            
            result = download_file(url_info['url'], url_info['filename'])
            download_results.append(result)
            
            if result['success']:
                downloaded_files.append({
                    'filename': result['filename'],
                    'size': result['size'],
                    'url_id': url_id
                })
                print(f"  ✓ 下载成功: {result['filename']} ({result['size']} 字节)")
            else:
                print(f"  ✗ 下载失败: {result['error']}")
    
    # 生成下载文件列表
    file_list = []
    for file_info in downloaded_files:
        size_kb = file_info['size'] / 1024
        file_list.append(f"- {file_info['filename']} ({size_kb:.1f} KB) - {file_info['url_id']}")
    
    # 设置GitHub Actions输出
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        if file_list:
            fh.write(f'downloaded_files={chr(10).join(file_list)}\n')
        else:
            fh.write('downloaded_files=没有文件被下载\n')
        
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