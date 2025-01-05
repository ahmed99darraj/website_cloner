from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup
import uuid
import json
from dotenv import load_dotenv
import shutil
import zipfile
from PIL import Image
from io import BytesIO
import base64
import logging
import ssl
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import io
from urllib.parse import urljoin
from flask import url_for

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تكوين المجلدات
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
CORS(app)  # تمكين CORS لجميع المسارات

# إعداد السجلات
logging.basicConfig(level=logging.DEBUG,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# المجلد المؤقت لحفظ الملفات
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clone', methods=['POST'])
def clone_website():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            logger.error("No URL provided")
            return jsonify({
                'success': False,
                'error': 'الرجاء إدخال رابط الموقع'
            })

        url = data['url'].strip()
        if not url:
            logger.error("Empty URL provided")
            return jsonify({
                'success': False,
                'error': 'الرجاء إدخال رابط الموقع'
            })

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Cloning website: {url}")

        # محاولة تحميل الموقع
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching website: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'لا يمكن الوصول إلى الموقع. تأكد من صحة الرابط.'
            })

        # تحليل HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # تحويل الروابط النسبية إلى مطلقة
        for tag in soup.find_all(['img', 'script', 'link', 'a']):
            if tag.get('src'):
                tag['src'] = urljoin(url, tag['src'])
            if tag.get('href'):
                tag['href'] = urljoin(url, tag['href'])

        # إنشاء معرف فريد للملف
        file_id = str(uuid.uuid4())
        file_path = os.path.join(TEMP_DIR, f'{file_id}.html')

        # حفظ الملف
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        logger.info(f"Website cloned successfully. File ID: {file_id}")
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': 'تم استنساخ الموقع بنجاح'
        })

    except Exception as e:
        logger.error(f"Error cloning website: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/preview/<file_id>')
def preview(file_id):
    try:
        file_path = os.path.join(TEMP_DIR, f'{file_id}.html')
        if not os.path.exists(file_path):
            logger.error(f"Preview file not found: {file_id}")
            return "الملف غير موجود", 404

        logger.info(f"Serving preview for {file_id}")
        
        # قراءة محتوى الملف
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تحليل HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # إضافة معرف الملف وملفات المحرر
        if not soup.head:
            soup.html.insert(0, soup.new_tag('head'))
        
        # إضافة معرف الملف
        script_tag = soup.new_tag('script')
        script_tag.string = f'window.FILE_ID = "{file_id}";'
        soup.head.append(script_tag)
        
        # إضافة CSS المحرر
        editor_css = soup.new_tag('link')
        editor_css['rel'] = 'stylesheet'
        editor_css['href'] = url_for('static', filename='css/editor.css', _external=True)
        soup.head.append(editor_css)
        
        # إضافة مكتبة jQuery
        jquery_script = soup.new_tag('script')
        jquery_script['src'] = 'https://code.jquery.com/jquery-3.7.1.min.js'
        soup.head.append(jquery_script)
        
        # إضافة JavaScript المحرر
        editor_js = soup.new_tag('script')
        editor_js['src'] = url_for('static', filename='js/editor.js', _external=True)
        soup.head.append(editor_js)
        
        # إضافة تهيئة المحرر
        init_script = soup.new_tag('script')
        init_script.string = """
            $(document).ready(function() {
                console.log('Document ready, initializing editor...');
                window.editor = new ElementEditor(document.body);
                
                // إضافة تأثيرات التحويم
                $('img, a, p, h1, h2, h3, h4, h5, h6, span, div').hover(
                    function() { $(this).addClass('editable-hover'); },
                    function() { $(this).removeClass('editable-hover'); }
                );
                
                // إضافة معالج النقر
                $('img, a, p, h1, h2, h3, h4, h5, h6, span, div').click(function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Element clicked:', this);
                    if (window.editor) {
                        window.editor.showEditor(this);
                    }
                });
            });
        """
        soup.head.append(init_script)
        
        # حفظ التغييرات
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        # إرسال الملف مع رؤوس الأمان المناسبة
        response = send_file(file_path)
        response.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data: blob:; media-src * data: blob:;"
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response
        
    except Exception as e:
        logger.error(f"Error serving preview: {str(e)}")
        return str(e), 500

@app.route('/update_element', methods=['POST'])
def update_element():
    try:
        data = request.get_json()
        file_id = request.args.get('file_id')
        
        if not file_id:
            return jsonify({'success': False, 'error': 'ملف غير موجود'}), 404
            
        print("Received update request:", data)  # إضافة سجل للتصحيح
        
        # إرجاع استجابة نجاح
        return jsonify({
            'success': True,
            'message': 'تم تحديث العنصر بنجاح'
        })
    except Exception as e:
        print("Error in update_element:", str(e))  # إضافة سجل للأخطاء
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'لم يتم تحديد ملف'
            })
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'لم يتم تحديد ملف'
            })
        
        # التحقق من نوع الملف
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return jsonify({
                'success': False,
                'error': 'نوع الملف غير مدعوم'
            })
        
        # إنشاء اسم فريد للملف
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # حفظ الملف
        file.save(file_path)
        
        # إنشاء URL للملف
        file_url = url_for('uploaded_file', filename=filename, _external=True)
        
        logger.info(f"Image uploaded successfully: {filename}")
        return jsonify({
            'success': True,
            'file_url': file_url
        })
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_file(os.path.join(UPLOAD_DIR, filename))
    except Exception as e:
        logger.error(f"Error serving uploaded file: {str(e)}")
        return str(e), 404

@app.route('/download/<file_id>')
def download_website(file_id):
    try:
        # التحقق من وجود الملف
        html_file = os.path.join(TEMP_DIR, f'{file_id}.html')
        if not os.path.exists(html_file):
            return 'الملف غير موجود', 404

        # إنشاء مجلد مؤقت للموقع
        site_dir = os.path.join(TEMP_DIR, f'site_{file_id}')
        if not os.path.exists(site_dir):
            os.makedirs(site_dir)

        # نسخ ملف HTML الرئيسي
        shutil.copy2(html_file, os.path.join(site_dir, 'index.html'))

        # نسخ الصور المحملة إذا وجدت
        assets_dir = os.path.join(site_dir, 'assets')
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        # قراءة ملف HTML للبحث عن الصور المحملة
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            
            # البحث عن الصور التي تم تحميلها
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if '/uploads/' in src:
                    # استخراج اسم الملف من المسار
                    filename = src.split('/')[-1]
                    original_path = os.path.join(UPLOAD_DIR, filename)
                    if os.path.exists(original_path):
                        # نسخ الصورة إلى مجلد الأصول
                        shutil.copy2(original_path, os.path.join(assets_dir, filename))
                        # تحديث مسار الصورة في HTML
                        img['src'] = f'assets/{filename}'

            # حفظ HTML المحدث
            with open(os.path.join(site_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(str(soup))

        # إنشاء ملف ZIP في الذاكرة
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # إضافة جميع الملفات إلى ZIP
            for root, _, files in os.walk(site_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, site_dir)
                    zf.write(file_path, arc_name)

        # حذف المجلد المؤقت
        shutil.rmtree(site_dir)

        # تجهيز الملف للتحميل
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'website_{file_id}.zip'
        )

    except Exception as e:
        logger.error(f"Error creating download: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
