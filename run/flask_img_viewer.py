import os
import argparse
import shutil
import math
from flask import Flask, render_template_string, send_from_directory, request, jsonify

app = Flask(__name__)

HTML_TEMPLATE = """

<!DOCTYPE html>
<html>
<head>
    <title>Gallery: {{ path }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; margin: 0; }
        header { position: sticky; top: 0; background: #1f1f1f; padding: 15px; border-bottom: 1px solid #333; z-index: 100; display: flex; justify-content: space-between; align-items: center; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; padding: 20px; }
        .img-card { position: relative; background: #252525; border-radius: 8px; overflow: hidden; border: 2px solid transparent; }
        .img-card img { width: 100%; height: 180px; object-fit: cover; cursor: pointer; }
        .img-info { padding: 8px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; }
        
        .controls { display: flex; gap: 15px; align-items: center; }
        .pagination { padding: 20px; text-align: center; }
        .btn { padding: 8px 16px; border-radius: 4px; border: none; cursor: pointer; font-weight: bold; background: #333; color: white; text-decoration: none; }
        .btn-delete { background: #ff4444; display: {{ 'block' if allow_delete else 'none' }}; }
        .btn:disabled { background: #222; color: #555; }
        
        /* Modal / Lightbox */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); }
        .modal-content { margin: auto; display: block; max-height: 90vh; max-width: 90%; margin-top: 2vh; }
        .nav-btn { position: absolute; top: 50%; transform: translateY(-50%); font-size: 50px; color: white; cursor: pointer; padding: 20px; user-select: none; }
        .nav-left { left: 10px; }
        .nav-right { right: 10px; }
        
        .checkbox-overlay { position: absolute; top: 10px; left: 10px; transform: scale(1.5); cursor: pointer; z-index: 5; }
    </style>
</head>
<body>

<header>
    <div><strong>{{ path }}</strong> ({{ total }} files)</div>
    <div class="controls">
        <label>Show: 
            <select onchange="location.href='?limit='+this.value">
                {% for l in [10, 25, 50, 100] %}
                <option value="{{ l }}" {{ 'selected' if l == limit }}>{{ l }}</option>
                {% endfor %}
            </select>
        </label>
        <button id="batchDeleteBtn" class="btn btn-delete" onclick="handleBatchDelete()" disabled>Delete Selected</button>
    </div>
</header>

<div class="gallery">
    {% for image in images %}
    <div class="img-card">
        <input type="checkbox" class="checkbox-overlay" value="{{ image }}" onchange="updateUI()">
        <img src="/images/{{ image }}" onclick="openModal({{ loop.index0 }})">
        <div class="img-info">
            <span title="{{ image }}">{{ image[:20] }}{{ '...' if image|length > 20 }}</span>
            <span style="cursor:pointer; color:#ff4444; {{ 'display:none' if not allow_delete }}" onclick="executeDelete(['{{ image }}'])">🗑</span>
        </div>
    </div>
    {% endfor %}
</div>

<div class="pagination">
    {% if page > 1 %}
    <a href="?page={{ page-1 }}&limit={{ limit }}" class="btn">Prev</a>
    {% endif %}
    <span>Page {{ page }} of {{ total_pages }}</span>
    {% if page < total_pages %}
    <a href="?page={{ page+1 }}&limit={{ limit }}" class="btn">Next</a>
    {% endif %}
</div>

<div id="myModal" class="modal">
    <span class="nav-btn nav-left" onclick="changeImage(-1)">&#10094;</span>
    <img class="modal-content" id="modalImg" onclick="closeModal()">
    <span class="nav-btn nav-right" onclick="changeImage(1)">&#10095;</span>
</div>
<script>
    const imageList = {{ images|tojson }};
    let currentIndex = 0;

    function openModal(index) {
        currentIndex = index;
        document.getElementById("myModal").style.display = "block";
        document.body.style.overflow = "hidden"; // Prevent background scrolling
        updateModalImage();
    }

    function closeModal() {
        document.getElementById("myModal").style.display = "none";
        document.body.style.overflow = "auto"; // Restore scrolling
    }

    function updateModalImage() {
        document.getElementById("modalImg").src = "/images/" + imageList[currentIndex];
    }

    function changeImage(dir) {
        currentIndex += dir;
        if (currentIndex < 0) currentIndex = imageList.length - 1;
        if (currentIndex >= imageList.length) currentIndex = 0;
        updateModalImage();
    }

    // Keyboard Navigation: Left, Right, and Escape
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById("myModal");
        if (modal.style.display === "block") {
            if (e.key === "ArrowLeft") {
                changeImage(-1);
            } else if (e.key === "ArrowRight") {
                changeImage(1);
            } else if (e.key === "Escape") {
                closeModal();
            }
        }
    });

    function updateUI() {
        const checkedCount = document.querySelectorAll('input[type="checkbox"]:checked').length;
        const btn = document.getElementById('batchDeleteBtn');
        if (btn) {
            btn.disabled = checkedCount === 0;
            btn.innerText = `Delete Selected (${checkedCount})`;
        }
    }

    async function handleBatchDelete() {
        const checked = Array.from(document.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
        if (confirm(`Archive ${checked.length} files?`)) executeDelete(checked);
    }

    async function executeDelete(fileList) {
        const response = await fetch('/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ filenames: fileList })
        });
        if (response.ok) location.reload();
    }
</script>

</body>
</html>
"""

@app.route('/')
def index():
    limit = request.args.get('limit', default=25, type=int)
    page = request.args.get('page', default=1, type=int)
    
    # Filter out hidden files
    all_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and not f.startswith('.')]
    all_files.sort(reverse=True)
    
    total = len(all_files)
    total_pages = math.ceil(total / limit)
    
    start = (page - 1) * limit
    end = start + limit
    paged_files = all_files[start:end]
    
    return render_template_string(HTML_TEMPLATE, 
                                images=paged_files, 
                                path=IMAGE_DIR, 
                                allow_delete=ALLOW_DELETE,
                                page=page,
                                limit=limit,
                                total=total,
                                total_pages=total_pages)

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.route('/delete', methods=['POST'])
def delete_images():
    if not ALLOW_DELETE:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    filenames = data.get('filenames', [])
    archive_path = os.path.join(IMAGE_DIR, ".archive")
    
    if not os.path.exists(archive_path):
        os.makedirs(archive_path)

    for filename in filenames:
        src = os.path.join(IMAGE_DIR, filename)
        if os.path.exists(src):
            # Archive behavior: .filename.bak
            dest = os.path.join(archive_path, f".{filename}.bak")
            shutil.move(src, dest)
            
    return jsonify({"success": True})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Absolute path to images")
    parser.add_argument("delete_flag", type=int, choices=[0, 1])
    parser.add_argument("-p","--port", help="Port for the image app")
    args = parser.parse_args()
    
    global IMAGE_DIR, ALLOW_DELETE
    IMAGE_DIR = os.path.abspath(args.path)
    ALLOW_DELETE = bool(args.delete_flag)
    
    app.run(host='0.0.0.0', port=args.port or 7000)
