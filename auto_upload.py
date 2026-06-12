#!/usr/bin/env python3
"""
Ted Chang Studio - 자동 업로드 스크립트
대기 폴더의 사진을 index.html에 추가하고 GitHub Pages에 배포합니다.
"""
import os, re, shutil, subprocess
from datetime import datetime
from collections import defaultdict

UPLOAD_BASE = os.path.expanduser("~/Pictures/TedChangUpload")
REPO_DIR = os.path.expanduser("~/초보프로젝트/tedchang-studio")
HTML_PATH = os.path.join(REPO_DIR, "index.html")
ARCHIVE_BASE = os.path.join(UPLOAD_BASE, "_archive")
CATEGORIES = ['Beauty','Models','Animals','Minimal','Stories','advert','nature','Streets']

def thumb(img_url):
    img = re.sub(r'/s\d+(-c)?/', '/s600/', img_url)
    img = re.sub(r'=s\d+(-c)?', '=s600', img)
    img = re.sub(r'/w\d+-h\d+/', '/w600-h400/', img)
    return img

def esc(text):
    return text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def scan_new_images():
    new_files = defaultdict(list)
    for cat in CATEGORIES:
        cat_dir = os.path.join(UPLOAD_BASE, cat)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if fname.lower().endswith(('.jpg','.jpeg','.png','.webp')):
                new_files[cat].append(os.path.join(cat_dir, fname))
    return new_files

def copy_to_repo(cat, src_path):
    dest_dir = os.path.join(REPO_DIR, "images", cat)
    os.makedirs(dest_dir, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_.\-]', '_', os.path.basename(src_path))
    dest_path = os.path.join(dest_dir, safe_name)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(safe_name)
        dest_path = os.path.join(dest_dir, base + "_" + datetime.now().strftime('%H%M%S') + ext)
    shutil.copy2(src_path, dest_path)
    return dest_path

def archive_original(src_path, cat):
    archive_dir = os.path.join(ARCHIVE_BASE, cat)
    os.makedirs(archive_dir, exist_ok=True)
    shutil.move(src_path, os.path.join(archive_dir, os.path.basename(src_path)))

def update_html(post_data):
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    summary = []
    for cat, posts in post_data.items():
        for title, img_path, body_text in posts:
            relative_url = os.path.relpath(img_path, REPO_DIR)
            title_esc = esc(title)
            body_esc = esc(body_text)
            img_js = relative_url.replace('"','&quot;')
            title_js = esc(title)
            body_js = esc(body_text)

            card_html = (
                '  <article class="post-card">\n'
                '    <a href="javascript:void(0)" data-img="' + img_js + '" data-title="' + title_js + '" data-body="' + body_js + '" class="post-img-link">\n'
                '      <img src="' + relative_url + '" alt="' + title_esc + '" loading="lazy">\n'
                '    </a>\n'
                '    <div class="post-text">\n'
                '      <h3>' + title + '</h3>\n'
                '      <p>' + body_esc + '</p>\n'
                '    </div>\n'
                '  </article>'
            )

            # Insert into cat-photo-grid
            grid_pattern = r'(<div class="cat-page" id="cat-' + cat + r'">.*?<div class="post-grid">\s*)'
            html = re.sub(grid_pattern, r'\1' + card_html.replace('\\', '\\\\') + '\n', html, count=1, flags=re.DOTALL)

            # Update cat-page header count
            count_pattern = r'(cat-' + cat + r'.*?cat-page-header"><h2>' + cat + r'</h2><p>\()(\d+)(\))'
            def make_updater():
                return lambda m: m.group(1) + str(int(m.group(2)) + 1) + m.group(3)
            html = re.sub(count_pattern, make_updater(), html, count=1, flags=re.DOTALL)

            # Update grid card count
            grid_count_pattern = r"(showCat\('" + cat + r"'\)[^>]*cat-count\">\()(\d+)(\))"
            html = re.sub(grid_count_pattern, make_updater(), html, count=1, flags=re.DOTALL)

            summary.append("  [" + cat + "] " + title)

    # Update backgrounds: keep all 8 unique
    used_bgs = set()
    for cat in CATEGORIES:
        bg_pattern = r"(showCat\('" + cat + r"'\)[^>]*background-image:url\()([^)]+)(\))"
        match = re.search(bg_pattern, html)
        if not match:
            continue
        current_bg = match.group(2)
        if current_bg in used_bgs:
            # Find alternative image for this category
            post_pattern = r'id="cat-' + cat + r'".*?<img src="([^"]+)"'
            all_imgs = re.findall(post_pattern, html, re.DOTALL)
            for img in all_imgs:
                if img not in used_bgs:
                    html = html.replace(current_bg, img)
                    used_bgs.add(img)
                    break
        else:
            used_bgs.add(current_bg)

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    return summary

def git_deploy():
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    msg = "Auto-upload: " + datetime.now().strftime('%Y-%m-%d %H:%M')
    subprocess.run(["git", "commit", "-m", msg], check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)

def main():
    print("[" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] TedChang Studio Auto Upload")
    new_files = scan_new_images()
    total_new = sum(len(v) for v in new_files.values())
    if total_new == 0:
        print("  No new images. Done.")
        return
    print("  Found " + str(total_new) + " new images")
    for cat, files in new_files.items():
        print("    " + cat + ": " + str(len(files)) + " images")

    post_data = defaultdict(list)
    for cat, files in new_files.items():
        for f in files:
            dest = copy_to_repo(cat, f)
            fname = os.path.splitext(os.path.basename(f))[0]
            title = fname.replace('_', ' ').replace('-', ' ')
            body = "새로운 사진입니다."
            post_data[cat].append((title, dest, body))
            archive_original(f, cat)

    summary = update_html(post_data)
    print("\n  Posts added:")
    for s in summary:
        print(s)

    git_deploy()
    print("\n  Deployed! (" + str(total_new) + " photos)")

if __name__ == "__main__":
    main()
