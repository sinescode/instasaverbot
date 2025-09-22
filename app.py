from flask import Flask, render_template, jsonify, send_file, request
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json
import os
from datetime import datetime
import io
import atexit

app = Flask(__name__)

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the LotteryResult model
class LotteryResult(db.Model):
    __tablename__ = 'lottery_results'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_number = db.Column(db.String(30), unique=True, nullable=False)  # increased from 20 → 30
    number = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(50), nullable=False)  # increased from 10 → 50
    premium = db.Column(db.Boolean, default=False)
    sum_value = db.Column(db.Integer)
    size = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'issueNumber': self.issue_number,
            'number': self.number,
            'color': self.color,
            'premium': self.premium,
            'sum': self.sum_value,
            'size': self.size,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

# URL for fetching lottery data
LOTTERY_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

def fetch_lottery_data():
    """Fetch lottery data from the API"""
    try:
        response = requests.get(LOTTERY_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching lottery data: {e}")
        return None

def determine_size(number):
    """Determine if number is small (0-4) or big (5-9)"""
    try:
        num = int(number)
        return "small" if 0 <= num <= 4 else "big"
    except ValueError:
        return "unknown"

def save_lottery_data(data):
    """Save lottery data to database"""
    if data and 'data' in data and 'list' in data['data']:
        for item in data['data']['list']:
            existing = LotteryResult.query.filter_by(issue_number=item['issueNumber']).first()
            if not existing:
                lottery_result = LotteryResult(
                    issue_number=item['issueNumber'],
                    number=item['number'],
                    color=item['color'],
                    premium=bool(int(item['premium'])),
                    sum_value=item['sum'],
                    size=determine_size(item['number'])
                )
                db.session.add(lottery_result)
        
        try:
            db.session.commit()
            print(f"Data saved successfully at {datetime.now()}")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving data: {e}")

def update_lottery_data():
    """Task to fetch and update lottery data every 30 seconds"""
    with app.app_context():
        print(f"Fetching new data at {datetime.now()}")
        data = fetch_lottery_data()
        if data:
            save_lottery_data(data)

# Initialize scheduler
scheduler = BackgroundScheduler()

def initialize():
    """Initialize the application"""
    # Create database tables
    db.create_all()
    
    # Fetch initial data
    print("Fetching initial data...")
    data = fetch_lottery_data()
    if data:
        save_lottery_data(data)
    
    # Start scheduler for periodic updates
    scheduler.add_job(func=update_lottery_data, trigger="interval", seconds=30)
    scheduler.start()
    print("Scheduler started")
    
    # Register shutdown function
    atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    """Display lottery results with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    pagination = LotteryResult.query.order_by(LotteryResult.issue_number.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    results = pagination.items
    
    total_records = LotteryResult.query.count()
    small_count = LotteryResult.query.filter_by(size='small').count()
    big_count = LotteryResult.query.filter_by(size='big').count()
    premium_count = LotteryResult.query.filter_by(premium=True).count()
    
    return render_template(
        'index.html', 
        results=results, 
        pagination=pagination,
        now=datetime.now(),
        total_records=total_records,
        small_count=small_count,
        big_count=big_count,
        premium_count=premium_count
    )

@app.route('/api/results')
def api_results():
    """API endpoint to get all results as JSON"""
    results = LotteryResult.query.order_by(LotteryResult.issue_number.desc()).all()
    return jsonify({
        "list": [result.to_dict() for result in results],
        "serviceTime": int(datetime.now().timestamp() * 1000),
        "code": 0,
        "msg": "Succeed",
        "msgCode": 0
    })

@app.route('/download')
def download_json():
    """Download all lottery data as JSON"""
    results = LotteryResult.query.order_by(LotteryResult.issue_number.desc()).all()
    data = {
        "list": [result.to_dict() for result in results],
        "serviceTime": int(datetime.now().timestamp() * 1000),
        "code": 0,
        "msg": "Succeed",
        "msgCode": 0
    }
    
    json_str = json.dumps(data, indent=2)
    mem = io.BytesIO()
    mem.write(json_str.encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        as_attachment=True,
        download_name='lottery_data.json',
        mimetype='application/json'
    )

if __name__ == '__main__':
    with app.app_context():
        initialize()
    app.run(host="0.0.0.0", port=10000, debug=True)
    
    
