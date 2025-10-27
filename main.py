from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_cors import CORS
from datetime import timedelta
import datetime

from models.User import User
from models.FileData import FileData
from models.CrawledData import CrawledData
from controller.FileDataDAO import FileDataDAO




app = Flask(__name__)
app.permanent_session_lifetime = timedelta(seconds=86400)
app.secret_key = "chatbot_secret"
CORS(app)

# Route hiển thị view chi tiết file
@app.route('/detail/<int:file_id>', methods=['GET'])
def detail_view(file_id):
    import io
    from docx import Document
    filedata_dao = FileDataDAO()
    file = filedata_dao.get_filedata_by_id(file_id)
    file_text = None
    if file and file.name.lower().endswith('.docx') and file.content:
        try:
            doc_stream = io.BytesIO(file.content)
            doc = Document(doc_stream)
            file_text = '\n'.join([p.text for p in doc.paragraphs])
        except Exception as e:
            file_text = f'Lỗi đọc file docx: {e}'
    elif file and file.content:
        try:
            file_text = file.content.decode('utf-8', errors='ignore')
        except Exception:
            file_text = '(Không thể decode nội dung file này)'
    if file:
        return render_template('DetailData.html', file=file, file_text=file_text)
    return 'File not found', 404


# API for statistics
@app.route('/api/statistic', methods=['GET'])
def api_statistic():
    from controller.StatisticDAO import StatisticDAO
    stat_dao = StatisticDAO()
    total_file = stat_dao.get_total_file()
    total_url = stat_dao.get_total_url()
    return jsonify({'totalFile': total_file, 'totalUrl': total_url})


# Route to render statistics view
@app.route('/statistic', methods=['GET'])
def statistic_view():
    return render_template('StatisticData.html')

# API lấy danh sách file cho thống kê
@app.route('/api/filedata', methods=['GET'])
def api_filedata():
    filedata_dao = FileDataDAO()
    file_list = filedata_dao.get_all_filedata()
    result = []
    for f in file_list:
        result.append({
            'id': f.id,
            'name': f.name,
            'status': f.status,
            'uploadDate': str(f.uploadDate),
            'user_id': f.u.id
        })
    return jsonify({'filedata': result})

# API lấy chi tiết nội dung file
@app.route('/api/filedata/<int:file_id>', methods=['GET'])
def api_filedata_detail(file_id):
    filedata_dao = FileDataDAO()
    file = filedata_dao.get_filedata_by_id(file_id)
    if file:
        return jsonify({'id': file.id, 'name': file.name, 'content': file.content, 'status': file.status, 'uploadDate': str(file.uploadDate), 'user_id': file.u.id})
    return jsonify({'error': 'File not found'}), 404

# API for crawled web data
@app.route('/api/crawleddata', methods=['GET'])
def api_crawleddata():
    from controller.CrawledDataDAO import CrawledDataDAO
    crawled_dao = CrawledDataDAO()
    crawled_list = crawled_dao.get_all_crawled_webs()
    result = []
    for c in crawled_list:
        result.append({
            'id': c.id,
            'url': c.url,
            'content': c.content,
            'crawlDate': str(c.crawlDate),
            'status': c.status,
            'user_id': c.u.id
        })
    return jsonify({'crawled_data': result})

@app.route("/addfiledata", methods=["GET"])
def add_file_data_view():
    return render_template("addFileData.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ''
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        filedata_dao = FileDataDAO()
        user = filedata_dao.check_login(username, password)
        if user:
            session["login"] = True
            session["fullname"] = user.username
            session["user"] = user.__dict__
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username / password!'
    return render_template('login.html', msg=msg)

@app.route("/", methods=["GET", "POST"])
def home():
    if "fullname" in session:
        fullname = session["fullname"]
        return render_template("index.html", fullname=fullname)
    return redirect(url_for('login'))

@app.route('/api/uploadfile', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        content = file.read()  # Đọc file nhị phân
        print("Đã nhận file:", file.filename, "Kích thước:", len(content), "bytes")
    except Exception as e:
        return jsonify({'error': f'Không đọc được file: {str(e)}'}), 400

    user_data = session.get('user')
    user = User(**user_data) if user_data else User(id='1', username='test', password='', email='', role='user')
    filedata_dao = FileDataDAO()
    filedata_dao.add_filedata(file.filename, content, datetime.date.today(), user, status='active')
    return jsonify({'status': 'success', 'filename': file.filename, 'message': 'Upload thành công!'})

@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
